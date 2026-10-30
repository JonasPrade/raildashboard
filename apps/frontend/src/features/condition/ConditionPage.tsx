import { useMemo, useState, type KeyboardEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { Info } from "lucide-react";
import {
    ActionIcon,
    Alert,
    Anchor,
    Badge,
    Container,
    Group,
    SegmentedControl,
    Select,
    Stack,
    Text,
    Title,
    Tooltip,
} from "@mantine/core";
import { LineChart } from "@mantine/charts";
import "@mantine/charts/styles.css";
import "../../shared/ui/charts.css";
import {
    useConditionPublicReports,
    useConditionPublicSeries,
    useConditionPublicYear,
    type ConditionAssetClass,
    type ConditionSeriesValue,
} from "../../shared/api/queries";
import { Stat, StatBand } from "../../shared/ui/Stat";
import { LoadingState } from "../../shared/ui/LoadingState";
import { ErrorState } from "../../shared/ui/ErrorState";
import { useIsMobile } from "../../shared/hooks/useBreakpoint";
import { CHART_SERIES, CONDITION_GRADE_COLOR } from "../../shared/theme/semanticColors";
import {
    GRADES,
    GRADE_LABEL,
    LAND_TILE,
    SCOPE_LABEL,
    SCOPE_SHORT,
    TRADE_LABEL,
    ValueIndex,
    classRows,
    formatDelta,
    formatInt,
    formatMrd,
    formatNote,
    formatPct,
    headlines,
    landRows,
    landStep,
    trend,
    type ClassRow,
    type Domain,
    type Scope,
    type SortKey,
} from "./conditionFormat";
import classes from "./ConditionPage.module.css";

const gradeColor = (grade: number) => CONDITION_GRADE_COLOR[grade as keyof typeof CONDITION_GRADE_COLOR];

function DistributionBar({ values }: { values: number[] }) {
    return (
        <div className={classes.dist} aria-hidden="true">
            {values.map((p, i) =>
                p > 0 ? (
                    <span
                        key={i}
                        style={{ width: `${p}%`, background: gradeColor(i + 1) }}
                        title={`${GRADE_LABEL[i + 1]}: ${formatPct(p)} %`}
                    />
                ) : null,
            )}
        </div>
    );
}

function GradeLegend() {
    return (
        <div className={classes.legend}>
            {GRADES.map((g) => (
                <span key={g}>
                    <i className={classes.swatch} style={{ background: gradeColor(g) }} />
                    {g} {GRADE_LABEL[g]}
                </span>
            ))}
        </div>
    );
}

function Headlines({ index, domain, year }: { index: ValueIndex; domain: Domain; year: number }) {
    const items = headlines(index, domain, year);
    return (
        <StatBand columns={4}>
            {items.map((h, i) => (
                <Stat
                    key={h.label}
                    value={
                        h.value === null ? (
                            "–"
                        ) : i === 0 ? (
                            // The one highlighted figure of the view (docs/DESIGN.md rule 3).
                            <span style={{ background: "var(--idt-highlight)", color: "var(--idt-ink)", outline: "2px solid var(--idt-highlight-line)", padding: "0 6px" }}>
                                {h.value.toLocaleString("de-DE", { minimumFractionDigits: h.digits, maximumFractionDigits: h.digits })}
                            </span>
                        ) : (
                            h.value.toLocaleString("de-DE", { minimumFractionDigits: h.digits, maximumFractionDigits: h.digits })
                        )
                    }
                    unit={h.unit ? ` ${h.unit}` : undefined}
                    title={h.label}
                    label={
                        [
                            h.note,
                            h.previous !== null && h.value !== null
                                ? `${year - 1}: ${h.previous.toLocaleString("de-DE", { minimumFractionDigits: h.digits })} (${formatDelta(h.value - h.previous, h.digits)})`
                                : null,
                        ]
                            .filter(Boolean)
                            .join(" · ") || undefined
                    }
                />
            ))}
        </StatBand>
    );
}

function Trend({ series, year }: { series: ConditionSeriesValue[]; year: number }) {
    const data = useMemo(() => trend(series, year), [series, year]);
    if (data.length < 2) return <Text size="sm" c="dimmed">Ein Verlauf entsteht ab zwei Berichtsjahren.</Text>;
    const values = data.flatMap((p) => [p.FAHRWEG, p.PERSONENBAHNHOF]).filter((v): v is number => v !== undefined);
    const lo = Math.floor((Math.min(...values) - 0.05) * 20) / 20;
    const hi = Math.ceil((Math.max(...values) + 0.05) * 20) / 20;
    const ticks = Array.from({ length: Math.round((hi - lo) * 20) + 1 }, (_, i) => Number((lo + i * 0.05).toFixed(2)));
    return (
        <Stack gap={6}>
            <LineChart
                h={240}
                data={data}
                dataKey="year"
                series={[
                    { name: "FAHRWEG", label: "Fahrweg (Netzzustandsnote)", color: CHART_SERIES[0] },
                    { name: "PERSONENBAHNHOF", label: "Personenbahnhöfe", color: CHART_SERIES[1] },
                ]}
                valueFormatter={formatNote}
                yAxisProps={{ domain: [lo, hi], ticks, tickFormatter: formatNote, width: 48, allowDataOverflow: true }}
                withLegend
                legendProps={{ verticalAlign: "bottom", height: 40 }}
                connectNulls
                curveType="linear"
            />
            <Text size="xs" c="dimmed">Achse ab {formatNote(lo)} · niedriger ist besser</Text>
        </Stack>
    );
}

function NetworkShares({ index, year }: { index: ValueIndex; year: number }) {
    const rows: { label: string; domain: Domain; scope: Scope }[] = [
        { label: "Gesamtnetz", domain: "FAHRWEG", scope: "GESAMT" },
        { label: "Hochleistungsnetz", domain: "FAHRWEG", scope: "HLN" },
        { label: "Flächennetz", domain: "FAHRWEG", scope: "FLN" },
        { label: "Personenbahnhöfe", domain: "PERSONENBAHNHOF", scope: "GESAMT" },
    ];
    const shown = rows
        .map((r) => ({
            ...r,
            note: index.get({ domain: r.domain, scope: r.scope, metric: "NOTE", year }),
            dist: index.distribution({ domain: r.domain, scope: r.scope, year }),
        }))
        .filter((r) => r.note !== null && r.dist !== null);
    return (
        <Stack gap="sm">
            <Text size="sm" fw={600} tt="uppercase" c="dimmed" style={{ letterSpacing: ".12em" }}>
                Notenverteilung {year}
            </Text>
            {shown.map((r) => (
                <div key={r.label} style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) 60px", gap: 10, alignItems: "end" }}>
                    <div style={{ minWidth: 0 }}>
                        <Text size="sm" fw={600} mb={4}>{r.label}</Text>
                        <DistributionBar values={r.dist!} />
                    </div>
                    <span className={classes.badge}>{formatNote(r.note!)}</span>
                </div>
            ))}
            <Text size="xs" c="dimmed">Anteil am bewerteten Wiederbeschaffungswert je Note.</Text>
            <GradeLegend />
        </Stack>
    );
}

function ClassDetail({ row, scopeLabel, domain, totalWbw }: { row: ClassRow; scopeLabel: string; domain: Domain; totalWbw: number | null }) {
    const unit = row.unit ?? "";
    const facts = [
        row.rated !== null
            ? `${formatInt(row.rated)} ${unit} bewertet${row.stock !== null && row.stock !== row.rated ? ` von ${formatInt(row.stock)} ${unit} im Bestand` : ""}`
            : null,
        row.wbw !== null && totalWbw ? `${formatPct((row.wbw / totalWbw) * 100)} % des bewerteten Wiederbeschaffungswerts` : null,
        row.need !== null
            ? domain === "FAHRWEG"
                ? `Erneuerungsbedarf (Note 4–6): ${formatInt(row.need)} ${unit}`
                : `Nachholbedarf ${formatNote(row.need)} Mrd. €`
            : null,
        row.previousNote !== null ? `Vorjahr ${formatNote(row.previousNote)} (${formatDelta(row.note - row.previousNote)})` : null,
    ].filter(Boolean);
    return (
        <div className={classes.card} style={{ marginTop: 16 }}>
            <Text fw={700}>{row.name} · {scopeLabel}</Text>
            <Text size="sm" c="dimmed" mb="sm">{facts.join(" · ")}</Text>
            {row.distribution ? (
                <div className={classes.tableWrap}>
                    <table className={classes.detailTable}>
                        <thead>
                            <tr>
                                <th>Note</th>
                                {GRADES.map((g) => (
                                    <th key={g} title={GRADE_LABEL[g]}>
                                        <i className={classes.swatch} style={{ background: gradeColor(g) }} />
                                        {g}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {row.counts && (
                                <tr>
                                    <td>Menge ({unit})</td>
                                    {row.counts.map((v, i) => <td key={i}>{formatInt(v)}</td>)}
                                </tr>
                            )}
                            <tr>
                                <td>Anteil WBW</td>
                                {row.distribution.map((v, i) => <td key={i}>{formatPct(v)} %</td>)}
                            </tr>
                        </tbody>
                    </table>
                </div>
            ) : (
                <Text size="sm" c="dimmed">
                    Für dieses Netz nennt der Bericht nur Note und Wiederbeschaffungswert, keine Notenverteilung.
                </Text>
            )}
        </div>
    );
}

function AssetClasses({
    index,
    assetClasses,
    series,
    domain,
    year,
}: {
    index: ValueIndex;
    assetClasses: ConditionAssetClass[];
    series: ConditionSeriesValue[];
    domain: Domain;
    year: number;
}) {
    const scopes = (["GESAMT", "HLN", "FLN", "SE"] as Scope[]).filter(
        (s) => domain === "FAHRWEG" && index.hasScope("FAHRWEG", s, year),
    );
    const [scopeChoice, setScope] = useState<Scope>("GESAMT");
    const scope: Scope = domain === "FAHRWEG" && scopes.includes(scopeChoice) ? scopeChoice : "GESAMT";
    const [sort, setSort] = useState<SortKey>("note");
    const [selected, setSelected] = useState<string | null>(null);
    const rows = useMemo(
        () => classRows(index, assetClasses, domain, scope, year, series, sort),
        [index, assetClasses, domain, scope, year, series, sort],
    );
    const slot = { domain, scope, year };
    const total = {
        note: index.get({ ...slot, metric: "NOTE" }),
        wbw: index.get({ ...slot, metric: "WBW_BEWERTET" }),
        dist: index.distribution(slot),
        need: index.get({ ...slot, metric: domain === "FAHRWEG" ? "ERNEUERUNGSBEDARF_MRD" : "NACHHOLBEDARF_MRD" }),
    };
    const current = rows.find((r) => r.key === selected) ?? rows[0] ?? null;
    const maxWbw = Math.max(...rows.map((r) => r.wbw ?? 0), 1);
    const select = (key: string) => setSelected(key);
    const onKey = (key: string) => (e: KeyboardEvent) => {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            select(key);
        }
    };
    const sortHeader = (key: SortKey, label: string, align?: "right") => (
        <button
            type="button"
            className={classes.sortButton}
            onClick={() => setSort(key)}
            aria-pressed={sort === key}
            style={align ? { textAlign: align } : undefined}
        >
            {label}
            {sort === key ? " ↓" : ""}
        </button>
    );

    return (
        <Stack gap="sm">
            <div className={classes.sectionHead}>
                <Title order={2} size={19}>Anlagenklassen</Title>
                <Text size="sm" c="dimmed">
                    {domain === "FAHRWEG" ? SCOPE_LABEL[scope] : "Personenbahnhöfe ohne Empfangsgebäude"} · Wiederbeschaffungswert in Mrd. €
                </Text>
                {scopes.length > 1 && (
                    <SegmentedControl
                        ml="auto"
                        size="xs"
                        value={scope}
                        onChange={(v) => {
                            setScope(v as Scope);
                            setSelected(null);
                        }}
                        data={scopes.map((s) => ({ value: s, label: SCOPE_SHORT[s] }))}
                    />
                )}
            </div>
            <div>
                <div className={classes.head}>
                    {sortHeader("name", "Anlagenklasse")}
                    {sortHeader("note", "Note")}
                    <span>Notenverteilung nach WBW</span>
                    {sortHeader("wbw", "WBW", "right")}
                    <span style={{ textAlign: "right" }}>{domain === "FAHRWEG" ? "Erneuerungsbedarf" : "Nachholbedarf"}</span>
                </div>
                {total.note !== null && (
                    <div className={`${classes.row} ${classes.total}`}>
                        <div className={classes.name}>{domain === "FAHRWEG" ? SCOPE_LABEL[scope] : "Personenbahnhöfe gesamt"}</div>
                        <span className={classes.badge}>{formatNote(total.note)}</span>
                        {total.dist ? <DistributionBar values={total.dist} /> : <span className={classes.muted}>–</span>}
                        <div className={classes.num}>{total.wbw !== null ? formatMrd(total.wbw) : "–"}</div>
                        <div className={classes.num}>{total.need !== null ? `${formatMrd(total.need)} Mrd. €` : "–"}</div>
                    </div>
                )}
                {rows.map((r) => (
                    <div
                        key={r.key}
                        className={`${classes.row} ${current?.key === r.key ? classes.selected : ""}`}
                        role="button"
                        tabIndex={0}
                        aria-pressed={current?.key === r.key}
                        aria-label={`${r.name}, Note ${formatNote(r.note)}`}
                        onClick={() => select(r.key)}
                        onKeyDown={onKey(r.key)}
                    >
                        <div className={classes.name}>
                            {r.name}
                            {r.trade && <span className={classes.sub}>{TRADE_LABEL[r.trade] ?? r.trade}</span>}
                        </div>
                        <span className={classes.badge}>
                            {formatNote(r.note)}
                        </span>
                        {r.distribution ? <DistributionBar values={r.distribution} /> : <span className={classes.muted}>–</span>}
                        <div className={classes.num}>
                            {r.wbw !== null ? formatMrd(r.wbw) : "–"}
                            {r.wbw !== null && <div className={classes.bar} style={{ width: `${Math.max(2, (r.wbw / maxWbw) * 100)}%` }} />}
                        </div>
                        <div className={classes.num}>
                            {r.need === null
                                ? "–"
                                : domain === "FAHRWEG"
                                  ? <>{formatInt(r.need)} <span className={classes.muted}>{r.unit}</span></>
                                  : <>{formatNote(r.need)} <span className={classes.muted}>Mrd. €</span></>}
                        </div>
                    </div>
                ))}
            </div>
            {current && (
                <ClassDetail
                    row={current}
                    scopeLabel={domain === "FAHRWEG" ? SCOPE_LABEL[scope] : "Personenbahnhöfe"}
                    domain={domain}
                    totalWbw={total.wbw}
                />
            )}
        </Stack>
    );
}

function Laender({ index, year }: { index: ValueIndex; year: number }) {
    const [domain, setDomain] = useState<Domain>("FAHRWEG");
    const [selected, setSelected] = useState<string | null>(null);
    const rows = landRows(index, domain, year);
    const average = index.get({ domain, scope: "GESAMT", metric: "NOTE", year });
    if (rows.length === 0 || average === null) return null;
    const byCode = new Map(rows.map((r) => [r.code, r]));
    const stepColor = [1, 2, 3, 4, 5].map((s) => gradeColor(s));
    const stepLabel = ["deutlich besser", "besser", `≈ Schnitt ${formatNote(average)}`, "schlechter", "deutlich schlechter"];
    const lo = 2.4;
    const hi = 3.6;
    const pos = (v: number) => `${Math.min(100, Math.max(0, ((v - lo) / (hi - lo)) * 100))}%`;
    const toggle = (code: string) => setSelected((s) => (s === code ? null : code));

    const cells = [];
    for (let r = 0; r < 7; r++) {
        for (let c = 0; c < 6; c++) {
            const code = Object.entries(LAND_TILE).find(([, p]) => p[0] === r && p[1] === c)?.[0];
            const land = code ? byCode.get(code) : undefined;
            if (!land) {
                cells.push(<div key={`${r}-${c}`} aria-hidden="true" />);
                continue;
            }
            const step = landStep(land.note, average);
            cells.push(
                <div
                    key={land.code}
                    role="button"
                    tabIndex={0}
                    aria-pressed={selected === land.code}
                    aria-label={`${land.name}: ${formatNote(land.note)}`}
                    title={`${land.name}: ${formatNote(land.note)}`}
                    className={`${classes.tile} ${step === 1 || step === 5 ? classes.tileStrong : ""} ${selected === land.code ? classes.tileSelected : ""}`}
                    style={{ background: stepColor[step - 1] }}
                    onClick={() => toggle(land.code)}
                    onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            toggle(land.code);
                        }
                    }}
                >
                    <b>{land.code}</b>
                    <span>{formatNote(land.note)}</span>
                </div>,
            );
        }
    }

    return (
        <Stack gap="sm">
            <div className={classes.sectionHead}>
                <Title order={2} size={19}>Bundesländer</Title>
                <Text size="sm" c="dimmed">Mittlere Zustandsnote · Strich = Bundesschnitt</Text>
                <SegmentedControl
                    ml="auto"
                    size="xs"
                    value={domain}
                    onChange={(v) => setDomain(v as Domain)}
                    data={[
                        { value: "FAHRWEG", label: "Fahrweg" },
                        { value: "PERSONENBAHNHOF", label: "Personenbahnhöfe" },
                    ]}
                />
            </div>
            <div className={classes.two}>
                <div className={classes.card}>
                    <div className={classes.tiles}>{cells}</div>
                    <div className={classes.legend} style={{ marginTop: 10 }}>
                        {stepLabel.map((l, i) => (
                            <span key={l}>
                                <i className={classes.swatch} style={{ background: stepColor[i] }} />
                                {l}
                            </span>
                        ))}
                    </div>
                </div>
                <div className={classes.card}>
                    <Text size="sm" fw={600} tt="uppercase" c="dimmed" mb={8} style={{ letterSpacing: ".12em" }}>
                        Rangfolge · beste zuerst
                    </Text>
                    {rows.map((l) => (
                        <div
                            key={l.code}
                            className={`${classes.rankRow} ${selected === l.code ? classes.selected : ""}`}
                        >
                            <span>{l.name}</span>
                            <div className={classes.rankTrack} aria-hidden="true">
                                <i style={{ width: pos(l.note) }} />
                                <em style={{ left: pos(average) }} />
                            </div>
                            <span className={classes.num} style={{ fontWeight: 700 }}>{formatNote(l.note)}</span>
                        </div>
                    ))}
                </div>
            </div>
        </Stack>
    );
}

export default function ConditionPage() {
    const isMobile = useIsMobile();
    const [searchParams, setSearchParams] = useSearchParams();
    const { data: reports, isLoading, isError, refetch } = useConditionPublicReports();
    const { data: series } = useConditionPublicSeries();
    const year = Number(searchParams.get("jahr")) || null;
    const current = reports?.find((r) => r.year === year) ?? reports?.[0] ?? null;
    const domain: Domain = searchParams.get("bereich") === "bahnhoefe" ? "PERSONENBAHNHOF" : "FAHRWEG";
    const yearData = useConditionPublicYear(current?.year ?? null);
    const index = useMemo(() => new ValueIndex(yearData.data?.values ?? []), [yearData.data]);

    const setParam = (key: string, value: string | null) =>
        setSearchParams(
            (prev) => {
                if (value) prev.set(key, value);
                else prev.delete(key);
                return prev;
            },
            { replace: true },
        );

    if (isLoading) return <Container py="xl"><LoadingState rows={6} /></Container>;
    if (isError) {
        return (
            <Container py="xl">
                <ErrorState onRetry={() => void refetch()}>Der Netzzustand konnte nicht geladen werden.</ErrorState>
            </Container>
        );
    }

    return (
        <Container size="xl" pt={{ base: "md", sm: "xl" }} pb="xl" px={{ base: 0, sm: "md" }}>
            <Stack gap="xl">
                <Group justify="space-between" align="flex-end" wrap="wrap" gap="sm">
                    <Stack gap={4}>
                        <Group gap="xs" align="center" wrap="nowrap">
                            <Title order={1}>Netzzustand</Title>
                            <Tooltip
                                label="Die DB InfraGO bewertet jährlich den Zustand von Fahrweg und Personenbahnhöfen mit Noten von
                                    1 (neuwertig) bis 6 (einschränkend), gewichtet nach Wiederbeschaffungswert, und leitet daraus den
                                    zustandsbasierten Erneuerungs- bzw. Nachholbedarf ab. Quelle ist der InfraGO-Zustandsbericht
                                    (bis 2023 Netzzustandsbericht)."
                                multiline
                                w={320}
                                withArrow
                                events={{ hover: true, focus: true, touch: true }}
                            >
                                <ActionIcon variant="subtle" color="gray" size="md" aria-label="Was ist der Netzzustand?">
                                    <Info size={16} />
                                </ActionIcon>
                            </Tooltip>
                        </Group>
                        <Text size="sm" c="dimmed">
                            InfraGO-Zustandsbericht · Noten 1 (neuwertig) bis 6 (einschränkend), gewichtet nach Wiederbeschaffungswert
                        </Text>
                    </Stack>
                    <Group gap="sm" wrap="wrap" w={isMobile ? "100%" : undefined} justify={isMobile ? "flex-start" : "flex-end"}>
                        {reports && reports.length > 1 ? (
                            <Select
                                aria-label="Jahrgang"
                                data={reports.map((r) => ({ value: String(r.year), label: `Bericht ${r.year}` }))}
                                value={String(current?.year ?? "")}
                                onChange={(v) => setParam("jahr", v)}
                                allowDeselect={false}
                                w={{ base: "100%", xs: 160 }}
                            />
                        ) : (
                            current && <Badge variant="outline">Bericht {current.year}</Badge>
                        )}
                        {current && (
                            <SegmentedControl
                                value={domain}
                                onChange={(v) => setParam("bereich", v === "PERSONENBAHNHOF" ? "bahnhoefe" : null)}
                                fullWidth={isMobile}
                                style={isMobile ? { flex: "1 1 100%", minWidth: 0 } : undefined}
                                data={[
                                    { value: "FAHRWEG", label: "Fahrweg" },
                                    { value: "PERSONENBAHNHOF", label: "Personenbahnhöfe" },
                                ]}
                            />
                        )}
                    </Group>
                </Group>

                {!current ? (
                    <Alert color="gray" variant="light" title="Noch kein Zustandsbericht freigegeben">
                        Sobald ein Jahrgang eingelesen und freigegeben ist, erscheinen hier Noten, Erneuerungsbedarf und Länderwerte.
                    </Alert>
                ) : yearData.isLoading ? (
                    <LoadingState rows={6} />
                ) : yearData.isError || !yearData.data ? (
                    <ErrorState onRetry={() => void yearData.refetch()}>Der Bericht {current.year} konnte nicht geladen werden.</ErrorState>
                ) : (
                    <>
                        <Headlines index={index} domain={domain} year={current.year} />

                        <Stack gap="sm">
                            <div className={classes.sectionHead}>
                                <Title order={2} size={19}>Entwicklung</Title>
                                <Text size="sm" c="dimmed">Zustandsnoten je Berichtsjahr</Text>
                            </div>
                            <div className={classes.two}>
                                <div className={classes.card}>
                                    <Trend series={series ?? []} year={current.year} />
                                </div>
                                <div className={classes.card}>
                                    <NetworkShares index={index} year={current.year} />
                                </div>
                            </div>
                        </Stack>

                        <AssetClasses
                            key={`${current.year}-${domain}`}
                            index={index}
                            assetClasses={yearData.data.classes}
                            series={series ?? []}
                            domain={domain}
                            year={current.year}
                        />

                        <Laender index={index} year={current.year} />

                        <Text size="sm" c="dimmed" style={{ borderTop: "2px solid var(--border-frame)", paddingTop: 12 }}>
                            Quelle: DB InfraGO,{" "}
                            {current.source_url ? (
                                <Anchor href={current.source_url} target="_blank" rel="noreferrer" size="sm">
                                    {current.title ?? `InfraGO-Zustandsbericht ${current.year}`}
                                </Anchor>
                            ) : (
                                current.title ?? `InfraGO-Zustandsbericht ${current.year}`
                            )}
                            {current.price_basis ? ` · Wiederbeschaffungswerte ${current.price_basis}` : ""}. Werte geprüft und freigegeben.
                        </Text>
                    </>
                )}
            </Stack>
        </Container>
    );
}
