import { useState, type ReactElement } from "react";
import { HoverCard } from "@mantine/core";
import { useMediaQuery } from "@mantine/hooks";

import { useProject } from "../../shared/api/queries";
import { LoadingState } from "../../shared/ui/LoadingState";
import ProjectSummaryCard from "./ProjectSummaryCard";
import { usePrefetchProjectPage } from "./usePrefetchProjectPage";

/** Only pointers that can hover get the preview; on touch a tap simply follows the link. */
const CAN_HOVER_QUERY = "(hover: hover) and (pointer: fine)";

type Props = {
    projectId: number;
    /** The project link; must accept a ref (Mantine `Anchor`/`Text`, router `Link`). */
    children: ReactElement;
};

/**
 * Shows the project's Kurzansicht (`ProjectSummaryCard`) while hovering a link
 * to it. The project is fetched only once the card opens — and that same fetch
 * warms the detail page, so the click afterwards renders without a spinner.
 */
export default function ProjectHoverCard({ projectId, children }: Props) {
    const canHover = useMediaQuery(CAN_HOVER_QUERY, false, { getInitialValueInEffect: false }) ?? false;
    const [opened, setOpened] = useState(false);
    const prefetchProjectPage = usePrefetchProjectPage();

    // Mantine still fires onOpen on a disabled HoverCard, so leave it out entirely.
    if (!canHover) return children;

    return (
        <HoverCard
            width={360}
            openDelay={350}
            closeDelay={100}
            position="bottom-start"
            withinPortal
            onOpen={() => {
                setOpened(true);
                prefetchProjectPage(projectId);
            }}
        >
            <HoverCard.Target>{children}</HoverCard.Target>
            <HoverCard.Dropdown>
                {opened && <ProjectHoverCardContent projectId={projectId} />}
            </HoverCard.Dropdown>
        </HoverCard>
    );
}

function ProjectHoverCardContent({ projectId }: { projectId: number }) {
    const { data: project, isLoading, isError } = useProject(projectId);
    if (isLoading) return <LoadingState />;
    if (isError || !project) return null;
    return <ProjectSummaryCard project={project} />;
}
