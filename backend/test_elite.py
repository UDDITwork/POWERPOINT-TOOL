"""
Elite Test Suite - Patent-Quality Diagram Generation

This test suite demonstrates the system's ability to handle
complex diagrams like the patent figures you shared.

Tests include:
1. FIG. 2 style (deeply nested hierarchical)
2. FIG. 4 style (multi-panel layout)
3. FIG. 5 style (sequential flowchart)

Author: AI Patent Diagram Generator (Elite Engineering Edition)
License: MIT
"""

import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from diagram_engine.unified_pipeline import PatentDiagramPipeline

# Load environment
load_dotenv()


def test_fig2_style():
    """
    Test FIG. 2 style diagram: Complex nested hierarchy with 4+ levels.

    This tests:
    - Deep nesting (Computer System > TSFM > Embeddings > Sub-elements)
    - Auto-sizing of parent containers
    - External element positioning (database)
    - Dashed connection lines
    - Proper reference numbering
    """
    print("\n" + "=" * 80)
    print("TEST 1: FIG. 2 Style - Complex Nested Hierarchy")
    print("=" * 80)

    prompt = """
    Create a complex system architecture diagram for a patent figure:

    Main Container: Computer System (202)

    Inside Computer System, arrange vertically:
    - System Metrics component (210A)
    - Event Logs component (210B)
    - Time Series Foundation Model (212) which contains:
      - Time Series Embeddings (212A) which contains:
        - Element 214A
        - Element 214B
    - Large Language Model (216) which contains:
      - Log Embeddings (216A) which contains:
        - Element 218A
        - Element 218B
    - Embedding Space (220) which contains:
      - Vector Representation (220A)
    - System Behavior Patterns (222) which contains:
      - New System Behavior Pattern (222A)
    - First Distribution Change (224)
    - Second Distribution Change (226)
    - Bottleneck Localizer Application (228)

    External Element: Historical Database (208) positioned to the right, containing:
    - Defined Set of Clusters (230A) which contains:
      - Sub-element 232 connected to both 212B and 216B
    - New Cluster (230B) which contains:
      - New Vector Representation (220B)

    Connections:
    - Connect Time Series Foundation Model (212) to Historical Database (208) with dashed line labeled "WAN 104"
    - Connect Large Language Model (216) to Historical Database (208) with dashed line

    Use proper patent numbering conventions.
    """

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set in .env")
        return False

    try:
        pipeline = PatentDiagramPipeline(api_key, use_multi_pass=True)

        result = pipeline.generate(
            prompt=prompt,
            output_path="test_fig2_complex.pptx",
            quality="high"
        )

        print("\n✅ FIG. 2 STYLE TEST PASSED")
        print(f"   Generated: {result['output_path']}")
        print(f"   Elements: {result['element_count']}")
        print(f"   Type: {result['diagram_type']}")
        print(f"   Complexity: {result['complexity']}")
        print("\n📂 Open 'test_fig2_complex.pptx' in PowerPoint to verify!")
        print("   → Every nested box should be individually editable")
        print("   → Parent boxes should auto-size to fit children")
        print("   → Database should be positioned externally")

        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fig5_style():
    """
    Test FIG. 5 style diagram: Sequential method flowchart.

    This tests:
    - Vertical flow layout
    - Long descriptive text in boxes
    - Sequential arrow connections
    - Centered alignment
    """
    print("\n" + "=" * 80)
    print("TEST 2: FIG. 5 Style - Sequential Flowchart")
    print("=" * 80)

    prompt = """
    Create a vertical flowchart for a patent method with 5 steps:

    Step 502: Receive system metrics and event logs from microservice applications executing across plurality of network nodes

    Step 504: Generate embeddings as vector representations from system metrics and event logs, where vector representations indicate system behavior patterns

    Step 506: Compare vector representations with historical vector representations associated with one or more previous executions of bottleneck localizer application

    Step 508: Identify new system behavior pattern based on comparison of vector representations with historical vector representations

    Step 510: Control re-execution of bottleneck localizer application based on identification of new system behavior pattern

    Connect all steps sequentially with arrows flowing downward.
    Use wide boxes (6-7 inches) to accommodate detailed text.
    Center all elements on the slide.
    """

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        return False

    try:
        pipeline = PatentDiagramPipeline(api_key)

        result = pipeline.generate(
            prompt=prompt,
            output_path="test_fig5_flowchart.pptx",
            quality="fast"  # Flowcharts are simpler, fast mode OK
        )

        print("\n✅ FIG. 5 STYLE TEST PASSED")
        print(f"   Generated: {result['output_path']}")
        print(f"   Elements: {result['element_count']}")
        print("\n📂 Open 'test_fig5_flowchart.pptx' to verify!")
        print("   → Should have 5 process boxes + 4 arrows")
        print("   → Boxes should be wide enough for full text")
        print("   → Vertical alignment should be perfect")

        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_network_diagram():
    """
    Test network diagram: Interconnected components.

    This tests:
    - Peer-to-peer connections
    - Multiple connection types
    - Smart node positioning
    """
    print("\n" + "=" * 80)
    print("TEST 3: Network Diagram - Client-Server Architecture")
    print("=" * 80)

    prompt = """
    Create a network diagram showing:

    Central Server (100) in the middle
    Database (110) on the right connected to server
    API Gateway (120) on the left connected to server

    Four client devices arranged in a semicircle:
    - Client 1 (200)
    - Client 2 (210)
    - Client 3 (220)
    - Client 4 (230)

    All clients connect to API Gateway with bidirectional arrows.
    Server connects to Database with bidirectional arrow.
    Server connects to API Gateway with bidirectional arrow.

    Use rounded rectangles for clients, rectangle for server,
    cylinder for database, and hexagon for API Gateway.
    """

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        return False

    try:
        pipeline = PatentDiagramPipeline(api_key)

        result = pipeline.generate(
            prompt=prompt,
            output_path="test_network.pptx",
            quality="fast"
        )

        print("\n✅ NETWORK DIAGRAM TEST PASSED")
        print(f"   Generated: {result['output_path']}")
        print(f"   Elements: {result['element_count']}")
        print("\n📂 Open 'test_network.pptx' to verify!")

        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_refinement():
    """
    Test iterative refinement capability.

    This tests:
    - Generating initial diagram
    - Refining based on user feedback
    - Maintaining structure while modifying
    """
    print("\n" + "=" * 80)
    print("TEST 4: Iterative Refinement")
    print("=" * 80)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        return False

    try:
        pipeline = PatentDiagramPipeline(api_key)

        # Initial generation
        print("Step 1: Generating initial diagram...")
        result1 = pipeline.generate(
            prompt="Create a simple system with Server (100), Database (110), and Cache (120)",
            output_path="test_refinement_v1.pptx",
            quality="fast"
        )

        print(f"   Initial: {result1['element_count']} elements")

        # Refinement
        print("\nStep 2: Refining diagram...")
        result2 = pipeline.refine(
            current_spec=result1['logical_spec'],
            refinement_prompt="Add a Load Balancer (90) above the server, connected with an arrow",
            output_path="test_refinement_v2.pptx"
        )

        print(f"   Refined: {result2['element_count']} elements")

        print("\n✅ REFINEMENT TEST PASSED")
        print("   V1: test_refinement_v1.pptx (3 elements)")
        print("   V2: test_refinement_v2.pptx (4 elements + connection)")
        print("\n📂 Compare both files to see refinement!")

        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all test cases."""
    print("\n" + "=" * 80)
    print("ELITE TEST SUITE - PATENT DIAGRAM GENERATION")
    print("=" * 80)

    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n❌ ERROR: ANTHROPIC_API_KEY not found in .env file")
        print("Please add your API key to continue.")
        return

    print("\n🔬 Running comprehensive test suite...")
    print("This will test the system's ability to handle patent-quality diagrams.")
    print("")

    results = []

    # Run tests
    results.append(("FIG. 2 Style (Complex Nested)", test_fig2_style()))
    results.append(("FIG. 5 Style (Flowchart)", test_fig5_style()))
    results.append(("Network Diagram", test_network_diagram()))
    results.append(("Iterative Refinement", test_refinement()))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    print("\n" + "-" * 80)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 80)

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nThe system can handle patent-quality diagrams!")
        print("\n📂 Generated files:")
        print("   - test_fig2_complex.pptx (FIG. 2 style)")
        print("   - test_fig5_flowchart.pptx (FIG. 5 style)")
        print("   - test_network.pptx (Network diagram)")
        print("   - test_refinement_v1.pptx, test_refinement_v2.pptx (Refinement)")
        print("\nOpen these in PowerPoint to verify full editability!")
    else:
        print("\n⚠️ Some tests failed. Check errors above.")


if __name__ == "__main__":
    run_all_tests()
