"""
Simple test script to verify the diagram generation system works.

Run this after setting up your ANTHROPIC_API_KEY in .env

Usage:
    python test_diagram.py
"""

import os
from dotenv import load_dotenv
from ai.claude_agent import ClaudeDiagramAgent
from diagram_engine.pptx_generator import PPTXDiagramGenerator

# Load environment variables
load_dotenv()

def test_simple_diagram():
    """Test generating a simple 3-step flowchart."""
    print("=" * 60)
    print("AI PATENT DIAGRAM GENERATOR - TEST")
    print("=" * 60)

    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ERROR: ANTHROPIC_API_KEY not found in .env file")
        print("Please add your API key to .env file")
        return False

    print("✅ API key found")
    print()

    # Test prompt
    prompt = """
    Create a simple flowchart with 3 steps:
    - Step 100: Input Data
    - Step 200: Process Data
    - Step 300: Output Result
    Connect them vertically with arrows.
    """

    print("📝 Test Prompt:")
    print(prompt)
    print()

    # Step 1: Initialize Claude agent
    print("🤖 Initializing Claude AI agent...")
    try:
        agent = ClaudeDiagramAgent(api_key=api_key)
        print("✅ Claude agent initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Claude: {e}")
        return False

    print()

    # Step 2: Generate diagram spec
    print("🧠 Generating diagram specification with Claude...")
    try:
        spec = agent.generate_diagram_spec(prompt)
        print(f"✅ Spec generated with {len(spec.get('elements', []))} elements")
        print()
        print("   Elements:")
        for elem in spec.get('elements', []):
            elem_type = elem.get('type', 'unknown')
            elem_id = elem.get('id', 'no-id')
            text = elem.get('text', '')
            if text:
                print(f"   - {elem_type} ({elem_id}): {text}")
            else:
                print(f"   - {elem_type} ({elem_id})")
    except Exception as e:
        print(f"❌ Failed to generate spec: {e}")
        return False

    print()

    # Step 3: Generate PPTX
    print("📊 Building PowerPoint diagram...")
    try:
        generator = PPTXDiagramGenerator()
        generator.create_from_json(spec)

        output_file = "test_diagram.pptx"
        generator.save(output_file)
        print(f"✅ Diagram saved to: {output_file}")
    except Exception as e:
        print(f"❌ Failed to generate PPTX: {e}")
        return False

    print()
    print("=" * 60)
    print("🎉 SUCCESS! Test completed successfully")
    print("=" * 60)
    print()
    print(f"📂 Open '{output_file}' in PowerPoint to see your diagram")
    print("   Every shape, arrow, and text box is fully editable!")
    print()

    return True


def test_refinement():
    """Test diagram refinement functionality."""
    print("=" * 60)
    print("TESTING DIAGRAM REFINEMENT")
    print("=" * 60)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ERROR: ANTHROPIC_API_KEY not set")
        return False

    # Create initial diagram
    print("📝 Creating initial diagram...")
    agent = ClaudeDiagramAgent(api_key=api_key)

    initial_prompt = "Create a block diagram with server (100) and database (110)"
    initial_spec = agent.generate_diagram_spec(initial_prompt)
    print(f"✅ Initial spec: {len(initial_spec['elements'])} elements")

    # Refine it
    print()
    print("📝 Refining diagram: 'Add a client box (200) connected to server'")
    refined_spec = agent.refine_diagram_spec(
        initial_spec,
        "Add a client box labeled 'Client (200)' connected to the server with an arrow"
    )
    print(f"✅ Refined spec: {len(refined_spec['elements'])} elements")

    # Generate refined PPTX
    generator = PPTXDiagramGenerator()
    generator.create_from_json(refined_spec)
    generator.save("test_refined_diagram.pptx")

    print()
    print("✅ Refinement test passed!")
    print("📂 Check 'test_refined_diagram.pptx'")
    print()

    return True


if __name__ == "__main__":
    # Run basic test
    success = test_simple_diagram()

    if success:
        print()
        response = input("Run refinement test? (y/n): ")
        if response.lower() == 'y':
            test_refinement()

    print()
    print("Done! Check the generated .pptx files.")
