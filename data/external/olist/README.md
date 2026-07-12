# Olist Brazilian E-Commerce

Source: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

This is the public, anonymized Olist e-commerce dataset covering roughly 100,000 Brazilian marketplace orders from 2016 to 2018. It is staged for DataPath's future multi-table query capability and is not yet published to the metric center.

## Local setup

```bash
uv run python -m scripts.download_olist
uv run python -m scripts.load_olist
uv run python -m scripts.validate_olist
```

The nine extracted CSV files are intentionally ignored by Git. `relationships.json` is the version-controlled contract for table grain, join cardinality, and future safe join paths.

## Current boundary

- Physical tables and source data: implemented.
- Row-count, key, and relationship validation: implemented.
- Semantic models and published metrics: not yet enabled.
- Multi-table planning and SQL Join compilation: not yet implemented.
- Natural-language questions use the published Olist fact-to-dimension join graph. Payment and review fact joins remain staged until aggregate-before-join is implemented.
