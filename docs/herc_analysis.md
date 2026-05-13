# herc_analysis (companion post-processing)

[**herc_analysis**](https://github.com/NatLabRockies/herc_analysis) is a companion Python repository for analyzing Hercules hybrid plant simulations. Install it into the same environment you use for Hercules when you want reusable loaders, plots, and summaries over HDF5 outputs (see the herc_analysis README and docs for features and API).

## Relationship to Hercules examples

The **examples** in this Hercules repository often include small, self-contained scripts that demonstrate basic post-processing (e.g. reading output files and plotting in place). **herc_analysis** builds on that idea with pre-built post-processing utilities tailored to Hercules HDF5 layout—use whichever fits your workflow; for full capability lists and usage, refer to herc_analysis documentation.

## `component_group`

Users may set an optional string `component_group` in each plant component block of the Hercules YAML input. If it is omitted, Hercules sets `component_group` equal to `component_name` (the YAML section key). The field does not change simulation behavior in Hercules; it is recorded in `h_dict` (including serialized metadata in output files) so tools such as herc_analysis can treat multiple named components as one logical entity—for example, summing their signals before downstream reporting.

See [Component Names, Types, and Categories](component_types.md) for the full picture of names, types, categories, and groups.
