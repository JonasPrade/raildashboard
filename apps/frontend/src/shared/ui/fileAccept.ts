/**
 * Checks a file against an `accept` string as used by `<input type="file">`:
 * a comma-separated list of MIME types (`application/pdf`), wildcards
 * (`image/*`) and extensions (`.pdf`). An empty string accepts everything.
 */
export function matchesAccept(file: File, accept: string | undefined): boolean {
    if (!accept) return true;
    const name = file.name.toLowerCase();
    const type = file.type.toLowerCase();
    return accept
        .split(",")
        .map((token) => token.trim().toLowerCase())
        .filter(Boolean)
        .some((token) => {
            if (token.startsWith(".")) return name.endsWith(token);
            if (token.endsWith("/*")) return type.startsWith(token.slice(0, -1));
            return type === token;
        });
}
