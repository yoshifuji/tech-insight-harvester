#!/usr/bin/env python3
"""
Complete pipeline runner for tech-insight-harvester
Runs all pipeline steps in sequence for testing and development
"""
import sys
import time
from pathlib import Path

def run_step(step_name: str, module_name: str):
    """Run a pipeline step and handle errors"""
    print(f"\n{'='*60}")
    print(f"🚀 Running {step_name}")
    print(f"{'='*60}")
    
    try:
        start_time = time.time()
        
        # Import and run the module
        module = __import__(module_name)
        module.main()
        
        elapsed = time.time() - start_time
        print(f"✅ {step_name} completed successfully in {elapsed:.2f}s")
        return True
        
    except Exception as e:
        print(f"❌ {step_name} failed: {e}")
        return False

def main():
    """Run the complete pipeline"""
    print("🤖 Tech Insight Harvester - Complete Pipeline")
    print("=" * 60)
    
    # Pipeline steps in order
    steps = [
        ("Article Crawling", "crawler"),
        ("Content Reading", "reader"),
        ("LLM Processing", "llm"),
        ("Markdown Generation", "md_writer"),
    ]
    
    # Optional steps (require additional setup)
    optional_steps = [
        ("Embedding Ingestion", "embed_ingest"),
    ]
    
    success_count = 0
    total_steps = len(steps)
    
    # Run main pipeline steps
    for step_name, module_name in steps:
        if run_step(step_name, module_name):
            success_count += 1
        else:
            print(f"\n⚠️  Pipeline stopped at {step_name}")
            break
    
    # Run optional steps if main pipeline succeeded
    if success_count == total_steps:
        print(f"\n{'='*60}")
        print("🔧 Running optional steps (may require additional setup)")
        print(f"{'='*60}")
        
        for step_name, module_name in optional_steps:
            run_step(step_name, module_name)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 Pipeline Summary")
    print(f"{'='*60}")
    print(f"✅ Completed: {success_count}/{total_steps} main steps")
    
    if success_count == total_steps:
        print("🎉 Pipeline completed successfully!")
        print("\nNext steps:")
        print("1. Check the 'docs/auto/' directory for generated Markdown files")
        print("2. Run 'npm start' to preview the Docusaurus site")
        print("3. Commit and push to trigger GitHub Actions")
    else:
        print("❌ Pipeline incomplete - check error messages above")
        sys.exit(1)

if __name__ == "__main__":
    main()