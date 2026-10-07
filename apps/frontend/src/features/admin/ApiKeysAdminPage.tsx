import { type FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import {
    Alert,
    Anchor,
    Badge,
    Button,
    Code,
    Container,
    CopyButton,
    Group,
    Loader,
    Modal,
    Radio,
    Stack,
    Table,
    Text,
    TextInput,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconChevronLeft } from "@tabler/icons-react";
import { ChronicleButton, ChronicleHeadline } from "../../components/chronicle";
import RequirePermission from "../../components/RequirePermission";
import { useAuth } from "../../lib/auth";
import { API_BASE } from "../../shared/api/client";
import {
    type ApiKey,
    type ApiKeyCreated,
    useAllApiKeys,
    useApiKeys,
    useCreateApiKey,
    useRevokeApiKey,
} from "../../shared/api/queries";
import { formatDateShort, formatDateTimeShort } from "../../shared/format";
import { ResponsiveTable } from "../../shared/ui/ResponsiveTable";

const MCP_PERMISSION = "mcp.access";
// A read-only key keeps only the MCP capability: every write tool needs a
// further capability (project.edit, todo.create, …) that the key then lacks.
const READ_ONLY_SCOPES = [MCP_PERMISSION];

type Preset = "read" | "full";

/** The backend stores naive UTC timestamps; mark them as UTC before formatting. */
function asUtc(value: string): string {
    return /[zZ]|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`;
}

function mcpUrl(): string {
    const base = API_BASE || window.location.origin;
    return `${base.replace(/\/$/, "")}/mcp`;
}

function mcpConfigSnippet(token: string): string {
    return JSON.stringify(
        {
            mcpServers: {
                raildashboard: {
                    type: "http",
                    url: mcpUrl(),
                    headers: { Authorization: `Bearer ${token}` },
                },
            },
        },
        null,
        2,
    );
}

function keyStatus(key: ApiKey): { label: string; color: string } {
    if (key.revoked_at) return { label: "Widerrufen", color: "gray" };
    if (key.expires_at && new Date(asUtc(key.expires_at)) <= new Date()) {
        return { label: "Abgelaufen", color: "orange" };
    }
    return { label: "Aktiv", color: "green" };
}

function scopeLabel(key: ApiKey): string {
    if (key.scopes === null || key.scopes === undefined) return "Wie Nutzer";
    const scopes = key.scopes;
    if (scopes.length === 1 && scopes[0] === MCP_PERMISSION) return "Nur lesen";
    return scopes.join(", ");
}

function CreateApiKeyModal({
    opened,
    onClose,
}: {
    opened: boolean;
    onClose: () => void;
}) {
    const [name, setName] = useState("");
    const [preset, setPreset] = useState<Preset>("read");
    const [error, setError] = useState<string | null>(null);
    const [created, setCreated] = useState<ApiKeyCreated | null>(null);
    const createKey = useCreateApiKey();

    const handleClose = () => {
        setName("");
        setPreset("read");
        setError(null);
        setCreated(null);
        onClose();
    };

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError(null);
        try {
            const result = await createKey.mutateAsync({
                name: name.trim(),
                scopes: preset === "read" ? READ_ONLY_SCOPES : null,
            });
            setCreated(result);
        } catch {
            setError("API-Key konnte nicht angelegt werden.");
        }
    };

    if (created) {
        const snippet = mcpConfigSnippet(created.token);
        return (
            <Modal opened={opened} onClose={handleClose} title="API-Key erstellt" size="lg">
                <Stack gap="sm">
                    <Alert color="orange" variant="light" title="Nur jetzt sichtbar">
                        Der Key wird nur dieses eine Mal angezeigt und nicht im Klartext
                        gespeichert. Kopieren Sie ihn jetzt. Geht er verloren, widerrufen Sie ihn
                        und legen einen neuen an.
                    </Alert>
                    <Code block style={{ wordBreak: "break-all", whiteSpace: "pre-wrap" }}>
                        {created.token}
                    </Code>
                    <CopyButton value={created.token}>
                        {({ copied, copy }) => (
                            <Button size="xs" variant="light" color={copied ? "green" : undefined} onClick={copy}>
                                {copied ? "Kopiert" : "Key kopieren"}
                            </Button>
                        )}
                    </CopyButton>
                    <Text size="sm">
                        Für Claude Code als <Code>.mcp.json</Code> im Projektordner (oder per{" "}
                        <Code>claude mcp add</Code>):
                    </Text>
                    <Code block style={{ whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
                        {snippet}
                    </Code>
                    <CopyButton value={snippet}>
                        {({ copied, copy }) => (
                            <Button size="xs" variant="light" color={copied ? "green" : undefined} onClick={copy}>
                                {copied ? "Kopiert" : "Konfiguration kopieren"}
                            </Button>
                        )}
                    </CopyButton>
                    <Text size="sm" c="dimmed">
                        Gültig bis {created.expires_at ? formatDateShort(asUtc(created.expires_at)) : "unbegrenzt"}.
                    </Text>
                    <Group justify="flex-end">
                        <Button onClick={handleClose}>Fertig</Button>
                    </Group>
                </Stack>
            </Modal>
        );
    }

    return (
        <Modal opened={opened} onClose={handleClose} title="Neuen API-Key anlegen" size="md">
            <form onSubmit={handleSubmit}>
                <Stack gap="sm">
                    {error && (
                        <Alert color="red" variant="light">
                            {error}
                        </Alert>
                    )}
                    <TextInput
                        label="Bezeichnung"
                        description="Wofür wird der Key genutzt, z. B. „Claude Code Laptop“"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        maxLength={100}
                        required
                        data-autofocus
                    />
                    <Radio.Group
                        label="Rechte"
                        value={preset}
                        onChange={(v) => setPreset(v as Preset)}
                    >
                        <Stack gap="xs" mt={4}>
                            <Radio
                                value="read"
                                label="Nur lesen (empfohlen)"
                                description="Der Assistent kann Projekte, Finanzierung, Planungsstand und Aufgaben abfragen, aber nichts ändern."
                            />
                            <Radio
                                value="full"
                                label="Wie mein Nutzer"
                                description="Zusätzlich Schreib-Tools: Projekte ändern, Beobachtungen, Texte und Aufgaben anlegen. Änderungen stehen im Änderungsprotokoll."
                            />
                        </Stack>
                    </Radio.Group>
                    <Text size="xs" c="dimmed">
                        Der Key läuft nach 90 Tagen ab und lässt sich jederzeit widerrufen.
                    </Text>
                    <Group justify="flex-end">
                        <Button variant="default" onClick={handleClose}>
                            Abbrechen
                        </Button>
                        <Button type="submit" loading={createKey.isPending} disabled={!name.trim()}>
                            Key erstellen
                        </Button>
                    </Group>
                </Stack>
            </form>
        </Modal>
    );
}

function KeysTable({
    keys,
    showOwner,
}: {
    keys: ApiKey[];
    showOwner?: boolean;
}) {
    const [confirmId, setConfirmId] = useState<number | null>(null);
    const revoke = useRevokeApiKey();

    const handleRevoke = async (key: ApiKey) => {
        try {
            await revoke.mutateAsync(key.id);
            setConfirmId(null);
            notifications.show({ color: "green", message: `Key „${key.name}“ wurde widerrufen.` });
        } catch {
            notifications.show({ color: "red", message: "Key konnte nicht widerrufen werden." });
        }
    };

    if (keys.length === 0) {
        return (
            <Text size="sm" c="dimmed">
                Noch keine API-Keys.
            </Text>
        );
    }

    return (
        <ResponsiveTable minWidth={760} striped withTableBorder>
            <Table.Thead>
                <Table.Tr>
                    <Table.Th>Bezeichnung</Table.Th>
                    {showOwner && <Table.Th>Nutzer</Table.Th>}
                    <Table.Th>Key</Table.Th>
                    <Table.Th>Rechte</Table.Th>
                    <Table.Th>Zuletzt genutzt</Table.Th>
                    <Table.Th>Gültig bis</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th />
                </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
                {keys.map((key) => {
                    const status = keyStatus(key);
                    const active = status.label === "Aktiv";
                    return (
                        <Table.Tr key={key.id}>
                            <Table.Td>{key.name}</Table.Td>
                            {showOwner && <Table.Td>{key.username}</Table.Td>}
                            <Table.Td>
                                <Code>rdb_{key.prefix}_…</Code>
                            </Table.Td>
                            <Table.Td>
                                <Text size="sm">{scopeLabel(key)}</Text>
                            </Table.Td>
                            <Table.Td>
                                <Text size="sm" c="dimmed">
                                    {key.last_used_at ? formatDateTimeShort(asUtc(key.last_used_at)) : "nie"}
                                </Text>
                            </Table.Td>
                            <Table.Td>
                                <Text size="sm" c="dimmed">
                                    {key.expires_at ? formatDateShort(asUtc(key.expires_at)) : "unbegrenzt"}
                                </Text>
                            </Table.Td>
                            <Table.Td>
                                <Badge color={status.color} variant="light" size="sm">
                                    {status.label}
                                </Badge>
                            </Table.Td>
                            <Table.Td>
                                {active &&
                                    (confirmId === key.id ? (
                                        <Group gap="xs" wrap="nowrap">
                                            <Button
                                                size="xs"
                                                color="red"
                                                loading={revoke.isPending}
                                                onClick={() => handleRevoke(key)}
                                            >
                                                Wirklich widerrufen
                                            </Button>
                                            <Button size="xs" variant="default" onClick={() => setConfirmId(null)}>
                                                Abbrechen
                                            </Button>
                                        </Group>
                                    ) : (
                                        <Button
                                            size="xs"
                                            variant="subtle"
                                            color="red"
                                            onClick={() => setConfirmId(key.id)}
                                        >
                                            Widerrufen
                                        </Button>
                                    ))}
                            </Table.Td>
                        </Table.Tr>
                    );
                })}
            </Table.Tbody>
        </ResponsiveTable>
    );
}

function ApiKeysPageContent() {
    const { can } = useAuth();
    const canManageUsers = can("user.manage");
    const [createOpened, { open: openCreate, close: closeCreate }] = useDisclosure(false);
    const { data: ownKeys, isLoading, isError } = useApiKeys();
    const { data: allKeys } = useAllApiKeys(canManageUsers);

    return (
        <Container size="lg" py="xl">
            <Stack gap="lg">
                <Anchor component={Link} to="/admin" size="sm" c="dimmed">
                    <Group gap={4} align="center">
                        <IconChevronLeft size={14} />
                        Zurück zur Administration
                    </Group>
                </Anchor>

                <Group justify="space-between">
                    <ChronicleHeadline as="h1">API-Keys & MCP</ChronicleHeadline>
                    <ChronicleButton onClick={openCreate}>Neuen Key anlegen</ChronicleButton>
                </Group>

                <Text size="sm">
                    Mit einem persönlichen API-Key können KI-Assistenten wie Claude Code über das Model
                    Context Protocol (MCP) auf das Dashboard zugreifen: Projekte suchen, Finanzierung
                    und Planungsstand abfragen und — mit einem Schreib-Key — Daten fortschreiben. Ein
                    Key hat nie mehr Rechte als sein Nutzer. MCP-Adresse: <Code>{mcpUrl()}</Code>
                </Text>

                <Stack gap="xs">
                    <ChronicleHeadline as="h2">Meine Keys</ChronicleHeadline>
                    {isLoading ? (
                        <Group justify="center" py="md">
                            <Loader />
                        </Group>
                    ) : isError ? (
                        <Alert color="red" variant="light" title="Fehler">
                            API-Keys konnten nicht geladen werden.
                        </Alert>
                    ) : (
                        <KeysTable keys={ownKeys ?? []} />
                    )}
                </Stack>

                {canManageUsers && (
                    <Stack gap="xs">
                        <ChronicleHeadline as="h2">Alle Keys</ChronicleHeadline>
                        <Text size="sm" c="dimmed">
                            Keys aller Nutzer — als Benutzerverwalter können Sie fremde Keys widerrufen.
                        </Text>
                        <KeysTable keys={allKeys ?? []} showOwner />
                    </Stack>
                )}
            </Stack>

            <CreateApiKeyModal opened={createOpened} onClose={closeCreate} />
        </Container>
    );
}

export default function ApiKeysAdminPage() {
    return (
        <RequirePermission
            perm={MCP_PERMISSION}
            message="API-Keys und MCP-Zugriff sind derzeit nur für Administratoren freigeschaltet."
        >
            <ApiKeysPageContent />
        </RequirePermission>
    );
}
