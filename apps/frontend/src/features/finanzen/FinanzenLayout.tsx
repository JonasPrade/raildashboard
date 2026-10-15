import { Container, SegmentedControl, Stack } from "@mantine/core";
import { Navigate, Outlet, useLocation, useNavigate } from "react-router-dom";
import { ChronicleHeadline } from "../../components/chronicle";
import { useIsMobile } from "../../shared/hooks/useBreakpoint";

/** Funding sources in the "Finanzen" menu; more can follow. */
const SECTIONS = [
    { value: "bedarfsplan", label: "Bedarfsplan Schiene" },
    { value: "gvfg", label: "GVFG" },
];

export default function FinanzenLayout() {
    const location = useLocation();
    const navigate = useNavigate();
    const isMobile = useIsMobile();
    const current = location.pathname.split("/")[2] ?? "";

    if (!SECTIONS.some((s) => s.value === current)) {
        return <Navigate to="/finanzen/bedarfsplan" replace />;
    }
    return (
        <Container size="xl" pt={{ base: "md", sm: "xl" }} px={{ base: 0, sm: "md" }}>
            <Stack gap="xs">
                <ChronicleHeadline as="h1">Finanzen</ChronicleHeadline>
                <SegmentedControl
                    data={SECTIONS}
                    value={current}
                    onChange={(value) => navigate(`/finanzen/${value}`)}
                    fullWidth={isMobile}
                    style={{ alignSelf: isMobile ? "stretch" : "flex-start" }}
                />
            </Stack>
            <Outlet />
        </Container>
    );
}
