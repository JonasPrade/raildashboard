import type { ComboboxItem, OptionsFilter } from "@mantine/core";

export const filterProjectOption: OptionsFilter = ({ options, search }) => {
    const tokens = search.toLowerCase().split(/\s+/).filter(Boolean);
    if (tokens.length === 0) return options;
    return (options as ComboboxItem[]).filter((option) => {
        const label = option.label.toLowerCase();
        return tokens.every((token) => label.includes(token));
    });
};
