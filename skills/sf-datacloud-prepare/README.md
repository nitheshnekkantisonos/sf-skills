# sf-datacloud-prepare

Ingestion and lake-preparation workflows for Salesforce Data Cloud.

## Use this skill for

- data streams
- Data Lake Objects (DLOs)
- data transforms
- Document AI setup and extraction
- deciding how a source dataset should enter Data Cloud
- classifying a dataset as `Profile`, `Engagement`, or `Other`

## Example requests

```text
"Create a Data Cloud stream from Contact"
"Inspect the DLO created by this stream"
"Help me create a transform for ingested data"
"Show me how to ingest this source system into Data Cloud"
```

## Common commands

```bash
sf data360 data-stream list -o myorg 2>/dev/null
sf data360 data-stream create-from-object -o myorg --object Contact --connection SalesforceDotCom_Home 2>/dev/null
sf data360 dlo get -o myorg --name Contact_Home__dll 2>/dev/null
sf data360 transform list -o myorg 2>/dev/null
```

## Key reminders

- confirm whether a dataset should be treated as `Profile`, `Engagement`, or `Other` before creating the stream
- some external database connectors can be created by API while stream creation still requires UI flow or org-specific browser automation

## References

- [SKILL.md](SKILL.md)
- [../sf-datacloud/assets/definitions/data-stream.template.json](../sf-datacloud/assets/definitions/data-stream.template.json)
- [CREDITS.md](CREDITS.md)

## License

MIT License - See [LICENSE](LICENSE).
