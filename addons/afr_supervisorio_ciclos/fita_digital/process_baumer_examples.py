#!/usr/bin/env python3
"""Process all Baumer Hivac2 example fitas, generate graphs, and profile performance."""

import sys
import time
import tracemalloc
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from reader_fita_digital.reader_fita_digital_baumer_hivac2 import ReaderFitaDigitalBaumerHivac2


BAUMER_EXEMPLOS_DIR = Path(__file__).parent / "reader_fita_digital" / "exemplos_fitas" / "baumer_hivac2"


def process_baumer_example(fita_path):
    """Process single Baumer example: read, generate graph, profile."""
    print(f"\nProcessing: {fita_path.name}")
    print("-" * 80)

    tracemalloc.start()
    start_time = time.perf_counter()

    try:
        # Read fita
        reader = ReaderFitaDigitalBaumerHivac2(str(fita_path))
        reader.read_file()
        reader.read_header()
        reader.read_body()
        state = reader.get_state()

        # Handle error states
        if state == "erro":
            print(f"  ERROR: Reader returned error state")
            tracemalloc.stop()
            return None

        header = reader.header if hasattr(reader, 'header') else {}
        body = reader.body if hasattr(reader, 'body') else {}

        # Extract data stats
        data_points = len(body.get('data', []))
        phases = len(body.get('fase', []))

        # Generate graph
        graph_result = reader.make_graph(header, body)

        # Save graph if returned
        graph_path = None
        if graph_result and isinstance(graph_result, bytes):
            graph_path = fita_path.parent / f"{fita_path.stem}.png"
            with open(graph_path, 'wb') as f:
                f.write(graph_result)
            print(f"  ✓ Graph saved: {graph_path.name}")
        elif isinstance(graph_result, str):
            # Base64 encoded image
            graph_path = fita_path.parent / f"{fita_path.stem}.png"
            with open(graph_path, 'wb') as f:
                f.write(base64.b64decode(graph_result))
            print(f"  ✓ Graph saved: {graph_path.name}")
        elif not graph_result:
            print(f"  ⚠ Graph generation returned no data")

        elapsed = time.perf_counter() - start_time
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / 1024 / 1024
        elapsed_ms = elapsed * 1000

        print(f"  ✓ Read complete: {data_points} data points, {phases} phases")
        print(f"  ✓ Time: {elapsed_ms:.2f} ms, Peak Memory: {peak_mb:.2f} MB")

        return {
            "filename": fita_path.name,
            "graph_path": str(graph_path) if graph_path else None,
            "data_points": data_points,
            "phases": phases,
            "elapsed_ms": elapsed_ms,
            "peak_memory_mb": peak_mb,
            "state": state,
            "status": "OK"
        }

    except Exception as e:
        tracemalloc.stop()
        print(f"  ERROR: {str(e)}")
        return {
            "filename": fita_path.name,
            "status": "FAILED",
            "error": str(e)
        }


def main():
    """Process all Baumer Hivac2 examples."""
    print("=" * 80)
    print("BAUMER HIVAC2 EXAMPLE FITA PROCESSOR")
    print("=" * 80)

    if not BAUMER_EXEMPLOS_DIR.exists():
        print(f"ERROR: Directory not found: {BAUMER_EXEMPLOS_DIR}")
        return

    # Find all .txt files
    fita_files = sorted(BAUMER_EXEMPLOS_DIR.glob("*.txt"))

    if not fita_files:
        print(f"No .txt files found in {BAUMER_EXEMPLOS_DIR}")
        return

    print(f"Found {len(fita_files)} example fita(s)\n")

    results = []
    for fita_path in fita_files:
        result = process_baumer_example(fita_path)
        if result:
            results.append(result)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()

    print(f"{'File':<50} {'Data Pts':<10} {'Phases':<10} {'Time (ms)':<12} {'Mem (MB)':<12} {'Status':<10}")
    print("-" * 105)

    for result in results:
        if result["status"] == "OK":
            print(
                f"{result['filename']:<50} "
                f"{result['data_points']:<10} "
                f"{result['phases']:<10} "
                f"{result['elapsed_ms']:<12.2f} "
                f"{result['peak_memory_mb']:<12.2f} "
                f"{result['state']:<10}"
            )
        else:
            print(
                f"{result['filename']:<50} "
                f"{'ERROR':<10} "
                f"{result.get('error', 'Unknown error'):<30}"
            )

    print()

    # Graph locations
    ok_results = [r for r in results if r["status"] == "OK"]
    if ok_results:
        print("Graph files saved:")
        for result in ok_results:
            if result.get('graph_path'):
                print(f"  - {Path(result['graph_path']).name}")

    print()
    print(f"Processed: {len(results)} files, {len(ok_results)} successful, {len(results) - len(ok_results)} failed")
    print()


if __name__ == "__main__":
    main()
