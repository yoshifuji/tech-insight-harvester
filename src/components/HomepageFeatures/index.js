import React from 'react';
import clsx from 'clsx';
import styles from './styles.module.css';

const FeatureList = [
  {
    title: '🤖 Automated Curation',
    description: (
      <>
        Our AI-powered pipeline automatically discovers, extracts, and curates
        the latest technology articles based on your defined keywords.
      </>
    ),
  },
  {
    title: '🧠 LLM Processing',
    description: (
      <>
        Each article is processed by GPT-4o to generate SEO-optimized titles,
        compelling summaries, and intelligent categorization.
      </>
    ),
  },
  {
    title: '🔍 Semantic Search',
    description: (
      <>
        Find relevant content instantly with our vector-powered semantic search
        that understands context and meaning, not just keywords.
      </>
    ),
  },
];

function Feature({title, description}) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center padding-horiz--md">
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures() {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
        
        <div className={styles.statsSection}>
          <h2>Pipeline Overview</h2>
          <div className={styles.pipelineSteps}>
            <div className={styles.step}>
              <h4>1. Crawl</h4>
              <p>Google Search API discovers fresh articles</p>
            </div>
            <div className={styles.step}>
              <h4>2. Extract</h4>
              <p>Clean content extraction from web pages</p>
            </div>
            <div className={styles.step}>
              <h4>3. Process</h4>
              <p>LLM generates titles, summaries, and tags</p>
            </div>
            <div className={styles.step}>
              <h4>4. Publish</h4>
              <p>Automatic Docusaurus site generation</p>
            </div>
            <div className={styles.step}>
              <h4>5. Index</h4>
              <p>Vector embeddings for semantic search</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}