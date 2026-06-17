import { type FormEvent, useEffect, useState } from "react";
import { Alert, Button, Modal, Select, Stack, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useRoles, useUpdateUser } from "../../shared/api/queries";

type EditableUser = {
    id: number;
    username: string;
    role: string;
};

type Props = {
    opened: boolean;
    onClose: () => void;
    user: EditableUser | null;
    /** True when editing the currently logged-in admin — their own role must stay fixed. */
    isSelf: boolean;
};

export function EditUserModal({ opened, onClose, user, isSelf }: Props) {
    const [username, setUsername] = useState("");
    const [role, setRole] = useState<string>("viewer");
    const [error, setError] = useState<string | null>(null);

    const updateUser = useUpdateUser();
    const { data: roles } = useRoles();
    const roleOptions = (roles ?? []).map((r) => ({
        value: r.name,
        label: r.description ? `${r.name} – ${r.description}` : r.name,
    }));

    useEffect(() => {
        if (user) {
            setUsername(user.username);
            setRole(user.role);
            setError(null);
        }
    }, [user]);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError(null);
        if (!user) return;

        const trimmed = username.trim();
        if (trimmed.length < 3) {
            setError("Benutzername muss mindestens 3 Zeichen lang sein.");
            return;
        }

        const payload: { userId: number; username?: string; role?: string } = { userId: user.id };
        if (trimmed !== user.username) payload.username = trimmed;
        if (!isSelf && role !== user.role) payload.role = role;

        if (payload.username === undefined && payload.role === undefined) {
            onClose();
            return;
        }

        try {
            await updateUser.mutateAsync(payload);
            notifications.show({
                color: "green",
                title: "Nutzer aktualisiert",
                message: `Die Änderungen an „${trimmed}" wurden gespeichert.`,
            });
            onClose();
        } catch {
            setError("Nutzer konnte nicht aktualisiert werden. Benutzername bereits vergeben?");
        }
    };

    return (
        <Modal opened={opened} onClose={onClose} title="Nutzer bearbeiten" size="sm">
            <form onSubmit={handleSubmit}>
                <Stack gap="sm">
                    {error && (
                        <Alert color="red" variant="light">
                            {error}
                        </Alert>
                    )}
                    <TextInput
                        label="Benutzername"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        minLength={3}
                        maxLength={50}
                        required
                    />
                    <Select
                        label="Rolle"
                        data={roleOptions}
                        value={role}
                        onChange={(v) => setRole(v ?? "viewer")}
                        allowDeselect={false}
                        disabled={isSelf}
                        description={isSelf ? "Die eigene Rolle kann nicht geändert werden." : undefined}
                    />
                    <Button type="submit" loading={updateUser.isPending} fullWidth mt="xs">
                        Speichern
                    </Button>
                </Stack>
            </form>
        </Modal>
    );
}
