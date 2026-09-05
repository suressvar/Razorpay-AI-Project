import asyncio
import traceback
from recovery_autopilot.services.orchestrator import orchestrator

async def main():
    try:
        count = await orchestrator.seed_demo_data(count=5, seed=42)
        print(f"SUCCESS: Seeded {count} cases")
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
