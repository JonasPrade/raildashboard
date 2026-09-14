import { describe, expect, it } from "vitest";

import {
    MAX_UPLOAD_BYTES,
    exceedsUploadLimit,
    tooLargeMessage,
    uploadErrorMessage,
} from "./uploads";

function fileOfSize(bytes: number, name = "bericht.pdf"): File {
    const file = new File(["x"], name, { type: "application/pdf" });
    Object.defineProperty(file, "size", { value: bytes });
    return file;
}

describe("exceedsUploadLimit", () => {
    it("accepts a file exactly at the limit", () => {
        expect(exceedsUploadLimit(fileOfSize(MAX_UPLOAD_BYTES))).toBe(false);
    });

    it("rejects a file one byte over the limit", () => {
        expect(exceedsUploadLimit(fileOfSize(MAX_UPLOAD_BYTES + 1))).toBe(true);
    });

    it("accepts the Haushalt report that triggered this limit (3.64 MB)", () => {
        expect(exceedsUploadLimit(fileOfSize(3_815_760))).toBe(false);
    });
});

describe("tooLargeMessage", () => {
    it("names the file and the limit", () => {
        expect(tooLargeMessage(fileOfSize(0, "EP12_Teil_B.pdf"))).toContain("EP12_Teil_B.pdf");
        expect(tooLargeMessage(fileOfSize(0))).toContain("50 MB");
    });
});

describe("uploadErrorMessage", () => {
    it("explains a 413 from the proxy, which carries no JSON body", () => {
        const message = uploadErrorMessage({ status: 413, message: "Request Entity Too Large" });
        expect(message).toContain("50 MB");
        expect(message).not.toContain("fehlgeschlagen");
    });

    it("prefers the backend detail when the API answered with one", () => {
        const message = uploadErrorMessage({
            status: 413,
            message: "",
            details: { detail: "Datei zu groß. Maximal 50 MB erlaubt." },
        });
        expect(message).toBe("Datei zu groß. Maximal 50 MB erlaubt.");
    });

    it("falls back to the caller's text for any other failure", () => {
        expect(uploadErrorMessage({ status: 500, message: "" }, "Auswertung fehlgeschlagen.")).toBe(
            "Auswertung fehlgeschlagen.",
        );
    });

    it("survives a thrown value that is not an ApiError", () => {
        expect(uploadErrorMessage(new Error("network"))).toBe("Upload fehlgeschlagen.");
    });
});
