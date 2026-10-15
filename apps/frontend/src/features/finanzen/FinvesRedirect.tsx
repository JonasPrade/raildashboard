import { Navigate, useLocation } from "react-router-dom";

/** Old links to /finves keep working (including ?q=). */
export default function FinvesRedirect() {
    const location = useLocation();
    return <Navigate to={`/finanzen/bedarfsplan${location.search}`} replace />;
}
