"""Batch processing example for Agent Protect SDK."""

import asyncio
from typing import List

from agent_protect_sdk import AgentProtectClient, ProtectionResult


async def check_batch(
    texts: List[str],
    client: AgentProtectClient,
) -> List[ProtectionResult]:
    """
    Check multiple texts concurrently.

    Args:
        texts: List of text strings to check
        client: Agent Protect client instance

    Returns:
        List of protection results
    """
    # Create tasks for concurrent execution
    tasks = [client.check_protection(text) for text in texts]

    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks)

    return results


async def main() -> None:
    """Demonstrate batch processing."""
    # Sample texts to check
    texts = [
        "This is a normal message",
        "Hello, how are you?",
        "Product inquiry about pricing",
        "Thank you for your help",
        "Another safe message here",
    ]

    async with AgentProtectClient(base_url="http://localhost:8000") as client:
        print(f"Checking {len(texts)} texts concurrently...\n")

        # Check all texts
        results = await check_batch(texts, client)

        # Display results
        print("Results:")
        print("-" * 80)
        for i, (text, result) in enumerate(zip(texts, results), 1):
            status = "✓ SAFE" if result.is_safe else "✗ UNSAFE"
            confidence = f"{result.confidence:.1%}"
            print(f"{i}. {status} ({confidence}): {text[:50]}...")

        print("-" * 80)

        # Summary statistics
        safe_count = sum(1 for r in results if r.is_safe)
        high_conf_count = sum(1 for r in results if r.is_confident(0.9))

        print(f"\nSummary:")
        print(f"  Total: {len(results)}")
        print(f"  Safe: {safe_count}")
        print(f"  Unsafe: {len(results) - safe_count}")
        print(f"  High confidence (>=90%): {high_conf_count}")


if __name__ == "__main__":
    print("=" * 60)
    print("Agent Protect SDK - Batch Processing Example")
    print("=" * 60)
    print()

    asyncio.run(main())

