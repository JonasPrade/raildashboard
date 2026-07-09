import type { ReactNode } from "react";
import { Alert, Container } from "@mantine/core";
import { useAuth } from "../lib/auth";

type Props = {
    perm: string;
    children: ReactNode;
    /** Override for the default denial message. */
    message?: string;
};

/** Renders its children only if the current user holds the given capability;
 * otherwise shows the standard "Kein Zugriff" alert (issue #74). */
export default function RequirePermission({ perm, children, message }: Props) {
    const { can } = useAuth();
    if (!can(perm)) {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Kein Zugriff">
                    {message ?? "Diese Seite ist nur für Editoren und Administratoren zugänglich."}
                </Alert>
            </Container>
        );
    }
    return <>{children}</>;
}
