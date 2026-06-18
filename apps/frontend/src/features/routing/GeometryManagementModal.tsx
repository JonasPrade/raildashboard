import { Modal } from "@mantine/core";

import type { Project } from "../../shared/api/queries";
import GeometryEditor from "./GeometryEditor";

type Props = {
    project: Project;
    opened: boolean;
    onClose: () => void;
};

export default function GeometryManagementModal({ project, opened, onClose }: Props) {
    return (
        <Modal
            opened={opened}
            onClose={onClose}
            fullScreen
            title="Geometrie verwalten"
            styles={{ body: { padding: 0, height: "calc(100% - 60px)", display: "flex" } }}
        >
            {/* Remount on each open so the editor starts from a clean state. */}
            {opened && (
                <GeometryEditor
                    project={project}
                    onSaved={onClose}
                    onCancel={onClose}
                    saveLabel="Übernehmen"
                    cancelLabel="Abbrechen"
                    height="100%"
                />
            )}
        </Modal>
    );
}
