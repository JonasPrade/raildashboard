import { modals } from "@mantine/modals";

type ConfirmModalOptions = Parameters<typeof modals.openConfirmModal>[0] & {
    /** Delete dialog: the confirming action turns red ("Löschen") instead of violet. */
    danger?: boolean;
};

/**
 * Confirm dialog after the Anwendungsebene ("Dialog"): the two actions sit in
 * the dialog foot (`.idt-modal-footer`, 2px ink line, fixed on phones) —
 * cancelling framed on the left, confirming filled on the right. A delete
 * dialog (`danger`) shows the red action in place of the violet one, never both.
 */
export function openConfirmModal({ danger = false, groupProps, cancelProps, confirmProps, ...options }: ConfirmModalOptions) {
    return modals.openConfirmModal({
        ...options,
        groupProps: {
            ...groupProps,
            // No inline margin: components.css spaces the foot below the body text
            // (which carries mb="md") and pushes it to the bottom edge on phones.
            mt: undefined,
            className: ["idt-modal-footer", groupProps?.className].filter(Boolean).join(" "),
        },
        cancelProps: { ...cancelProps, variant: "default" },
        confirmProps: { ...confirmProps, variant: "filled", color: danger ? "red" : undefined },
    });
}
