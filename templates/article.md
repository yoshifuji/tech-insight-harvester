---
title: "{{ seo_title }}"
description: "{{ summary.split('.')[0] }}."
tags: [{{ tag }}]
slug: {{ slug }}
authors: 
  - name: {{ author or 'Tech Insight Harvester' }}
    title: Content Curator
    url: {{ url }}
hide_table_of_contents: false
---

# {{ seo_title }}

:::info Article Summary
{{ summary }}
:::

## Original Article

**Source:** [{{ title }}]({{ url }})  
**Published:** {{ published_date or 'Date not available' }}  
**Author:** {{ author or 'Unknown' }}  
**Domain:** {{ source_domain }}

---

## Content

{{ content }}

---

## Metadata

<details>
<summary>Technical Details</summary>

- **Crawled:** {{ crawled_at }}
- **Processed:** {{ llm_processed_at }}
- **Word Count:** {{ word_count }}
- **Extraction Method:** {{ extraction_method }}
- **LLM Model:** {{ llm_model }}
- **Keyword:** {{ keyword }}

</details>

## Structured Data

```json
{{ json_ld | tojson(indent=2) }}
```

---

*This article was automatically curated and processed by Tech Insight Harvester. [View source]({{ url }})*