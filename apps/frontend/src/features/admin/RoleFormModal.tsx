import { type FormEvent, useEffect, useMemo, useState } from "react";
import {
    Alert,
    Button,
    Checkbox,
    Divider,
    Modal,
    Stack,
    Text,
    TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
    useCreateRole,
    usePermissions,
    useUpdateRole,
    type Role,
} from "../../shared/api/queries";

type Props = {
    opened: boolean;
    onClose: () => void;
    role: Role | null;
};

export function RoleFormModal({ opened, onClose, role }: Props) {
    const isEdit = role !== null;
    const isSystem = role?.is_system ?? false;
    // The admin system role is an implicit super-admin: its capabilities are
    // fixed (all of them) and cannot be edited.
    const isAdmin = role?.name === "admin";

    const { data: permissions } = usePermissions();
    const createRole = useCreateRole();
    const updateRole = useUpdateRole();

    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [selected, setSelected] = useState<Set<string>>(new Set());
    const [error, setError] = useState<string | null>(null);

    const allKeys = useMemo(
        () => (permissions ?? []).map((p) => p.key),
        [permissions],
    );

    useEffect(() => {
        if (!opened) return;
        setError(null);
        setName(role?.name ?? "");
        setDescription(role?.description ?? "");
        if (role?.name === "admin") {
            setSelected(new Set(allKeys));
        } else {
            setSelected(new Set(role?.permissions ?? []));
        }
    }, [opened, role, allKeys]);

    // Group the catalog by capability group, preserving catalog order.
    const groups = useMemo(() => {
        const ordered: { group: string; items: { key: string; label: string }[] }[] = [];
        for (const perm of permissions ?? []) {
            let bucket = ordered.find((g) => g.group === perm.group);
            if (!bucket) {
                bucket = { group: perm.group, items: [] };
                ordered.push(bucket);
            }
            bucket.items.push({ key: perm.key, label: perm.label });
        }
        return ordered;
    }, [permissions]);

    const toggle = (key: string, checked: boolean) => {
        setSelected((prev) => {
            const next = new Set(prev);
            if (checked) next.add(key);
            else next.delete(key);
            return next;
        });
    };

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError(null);

        const trimmedName = name.trim();
        if (!isSystem && trimmedName.length < 1) {
            setError("Bitte einen Rollennamen angeben.");
            return;
        }

        const permissionKeys = Array.from(selected);
        const trimmedDescription = description.trim() || null;

        try {
            if (isEdit && role) {
                await updateRole.mutateAsync({
                    roleId: role.id,
                    // System roles keep their name/description; only permissions change.
                    ...(isSystem ? {} : { name: trimmedName, description: trimmedDescription }),
                    ...(isAdmin ? {} : { permissions: permissionKeys }),
                });
                notifications.show({
                    color: "green",
                    title: "Rolle gespeichert",
                    message: `Die Rolle „${role.name}" wurde aktualisiert.`,
                });
            } else {
                await createRole.mutateAsync({
                    name: trimmedName,
                    description: trimmedDescription,
                    permissions: permissionKeys,
                });
                notifications.show({
                    color: "green",
                    title: "Rolle angelegt",
                    message: `Die Rolle „${trimmedName}" wurde erstellt.`,
                });
            }
            onClose();
        } catch {
            setError(
                isEdit
                    ? "Die Rolle konnte nicht gespeichert werden."
                    : "Die Rolle konnte nicht angelegt werden. Name bereits vergeben?",
            );
        }
    };

    return (
        <Modal
            opened={opened}
            onClose={onClose}
            title={isEdit ? "Rolle bearbeiten" : "Neue Rolle anlegen"}
            size="md"
        >
            <form onSubmit={handleSubmit}>
                <Stack gap="sm">
                    {error && (
                        <Alert color="red" variant="light">
                            {error}
                        </Alert>
                    )}
                    <TextInput
                        label="Name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        disabled={isSystem}
                        description={isSystem ? "Systemrollen können nicht umbenannt werden." : undefined}
                        maxLength={50}
                        required={!isSystem}
                    />
                    <TextInput
                        label="Beschreibung"
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        disabled={isSystem}
                        maxLength={255}
                    />

                    <Divider label="Berechtigungen" labelPosition="left" />

                    {isAdmin && (
                        <Alert color="gray" variant="light">
                            Der Admin hat als Super-Administrator immer alle Berechtigungen.
                        </Alert>
                    )}

                    <Stack gap="md">
                        {groups.map((g) => (
                            <Stack key={g.group} gap={6}>
                                <Text size="sm" fw={600}>{g.group}</Text>
                                {g.items.map((item) => (
                                    <Checkbox
                                        key={item.key}
                                        label={item.label}
                                        checked={selected.has(item.key)}
                                        disabled={isAdmin}
                                        onChange={(e) => toggle(item.key, e.currentTarget.checked)}
                                    />
                                ))}
                            </Stack>
                        ))}
                    </Stack>

                    <Button
                        type="submit"
                        loading={createRole.isPending || updateRole.isPending}
                        fullWidth
                        mt="xs"
                    >
                        {isEdit ? "Speichern" : "Rolle anlegen"}
                    </Button>
                </Stack>
            </form>
        </Modal>
    );
}
