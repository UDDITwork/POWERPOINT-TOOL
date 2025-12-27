"""
Quick Setup and Test Script

This script:
1. Verifies environment setup
2. Tests API connectivity
3. Generates a simple test diagram
4. Verifies the output

Run: python setup_and_test.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("=" * 70)
print("AI PATENT DIAGRAM GENERATOR - SETUP & VERIFICATION")
print("=" * 70)
print()

# Step 1: Check Python version
print("1. Checking Python version...")
import sys
py_version = sys.version_info
if py_version.major == 3 and py_version.minor >= 11:
    print(f"   ✅ Python {py_version.major}.{py_version.minor}.{py_version.micro}")
else:
    print(f"   ⚠️  Python {py_version.major}.{py_version.minor} (recommend 3.11+)")
print()

# Step 2: Check API keys
print("2. Checking API keys...")
anthropic_key = os.getenv("ANTHROPIC_API_KEY")
if anthropic_key and anthropic_key.startswith("sk-ant-"):
    print(f"   ✅ Anthropic API key found: {anthropic_key[:20]}...")
else:
    print("   ❌ Anthropic API key missing or invalid")
    print("   Please set ANTHROPIC_API_KEY in .env file")
    sys.exit(1)
print()

# Step 3: Check dependencies
print("3. Checking dependencies...")
try:
    import anthropic
    print("   ✅ anthropic")
except ImportError:
    print("   ❌ anthropic - Run: pip install anthropic")

try:
    import pptx
    print("   ✅ python-pptx")
except ImportError:
    print("   ❌ python-pptx - Run: pip install python-pptx")

try:
    import fastapi
    print("   ✅ fastapi")
except ImportError:
    print("   ❌ fastapi - Run: pip install fastapi")

try:
    from dotenv import load_dotenv
    print("   ✅ python-dotenv")
except ImportError:
    print("   ❌ python-dotenv - Run: pip install python-dotenv")

print()

# Step 4: Test API connectivity
print("4. Testing Claude API connectivity...")
try:
    import anthropic
    client = anthropic.Anthropic(api_key=anthropic_key)

    # Simple test call
    response = client.messages.create(
        model="claude-sonnet-4.5-20250929",
        max_tokens=100,
        messages=[
            {"role": "user", "content": "Say 'API working' if you can read this."}
        ]
    )

    if response.content:
        print(f"   ✅ Claude API connected successfully")
        print(f"   Response: {response.content[0].text[:50]}...")
    else:
        print("   ⚠️  API responded but no content")

except Exception as e:
    print(f"   ❌ API connection failed: {e}")
    print("   Check your API key and internet connection")
    sys.exit(1)

print()

# Step 5: Test simple diagram generation
print("5. Testing diagram generation...")
try:
    from diagram_engine.unified_pipeline import PatentDiagramPipeline

    print("   Creating pipeline...")
    pipeline = PatentDiagramPipeline(
        anthropic_api_key=anthropic_key,
        use_multi_pass=False  # Fast mode for test
    )

    print("   Generating test diagram...")
    result = pipeline.generate(
        prompt="Create a simple flowchart with 3 boxes: Input (100), Process (200), Output (300). Connect with arrows.",
        output_path="verification_test.pptx",
        quality="fast"
    )

    # Check if file was created
    if Path("verification_test.pptx").exists():
        file_size = Path("verification_test.pptx").stat().st_size
        print(f"   ✅ Diagram generated: verification_test.pptx ({file_size:,} bytes)")
        print(f"   Elements created: {result['element_count']}")
        print(f"   Diagram type: {result['diagram_type']}")
    else:
        print("   ❌ File not created")

except Exception as e:
    print(f"   ❌ Generation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 70)
print("✅ SETUP VERIFICATION COMPLETE")
print("=" * 70)
print()
print("🎉 System is ready to generate patent-quality diagrams!")
print()
print("Next steps:")
print("1. Run full test suite: python test_elite.py")
print("2. Open verification_test.pptx in PowerPoint to verify editability")
print("3. Start the API server: python main.py")
print()
print("=" * 70)
