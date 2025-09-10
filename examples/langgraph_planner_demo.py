"""
Demo script for the LangGraph-based task planner

Shows how to use the new planner to execute tasks with automatic
agent pod coordination and MCP tool integration.
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lab_agent.planner import TaskGraphPlanner
from lab_agent.planner.agent_state import TaskSpec, RunLevel, Priority
from lab_agent.playground.mcp_manager import MCPManager
from lab_agent.utils.logger import get_logger


async def demo_cooldown_task():
    """Demo a complex experimental workflow"""
    
    logger = get_logger(__name__)
    
    # Initialize components
    mcp_manager = MCPManager()
    planner = TaskGraphPlanner(mcp_manager)
    
    # Create a complex experimental task
    task_spec = TaskSpec(
        task_id="demo_cooldown_001",
        goal="Cooldown device D14, then 2D gate map at 20 mK",
        constraints=["runlevel:dry-run", "window:21:00-07:00", "max_power=2mW"],
        artifacts=["device_map/D14.json"],
        owner="demo_user",
        priority=Priority.NORMAL,
        runlevel=RunLevel.DRY_RUN,
        tags=["experiment", "cooldown", "gate-scan", "demo"]
    )
    
    logger.info("Starting cooldown workflow demo...")
    logger.info(f"Task: {task_spec.goal}")
    
    # Execute the task
    result = await planner.execute_task(task_spec)
    
    # Display results
    print("\n" + "="*60)
    print("WORKFLOW EXECUTION RESULTS")
    print("="*60)
    print(f"Task ID: {result.task_id}")
    print(f"Status: {result.status}")
    print(f"Execution Time: {result.execution_time:.2f} seconds")
    print(f"Nodes Executed: {', '.join(result.nodes_executed)}")
    print(f"Artifacts Created: {len(result.artifacts)}")
    
    if result.errors:
        print(f"Errors: {len(result.errors)}")
        for error in result.errors:
            print(f"  - {error}")
    
    print(f"\nSummary: {result.summary}")
    print("="*60)


async def demo_arxiv_research():
    """Demo a literature research workflow"""
    
    logger = get_logger(__name__)
    
    # Initialize components
    mcp_manager = MCPManager()
    planner = TaskGraphPlanner(mcp_manager)
    
    # Create a research task
    task_spec = TaskSpec(
        task_id="demo_research_001", 
        goal="Find and analyze recent papers about 2D materials and quantum dots",
        owner="demo_user",
        priority=Priority.NORMAL,
        runlevel=RunLevel.DRY_RUN,
        tags=["research", "arxiv", "2D_materials", "demo"]
    )
    
    logger.info("Starting ArXiv research demo...")
    logger.info(f"Task: {task_spec.goal}")
    
    # Execute the task
    result = await planner.execute_task(task_spec)
    
    # Display results
    print("\n" + "="*60)
    print("RESEARCH WORKFLOW RESULTS")
    print("="*60)
    print(f"Task ID: {result.task_id}")
    print(f"Status: {result.status}")
    print(f"Execution Time: {result.execution_time:.2f} seconds")
    print(f"Nodes Executed: {', '.join(result.nodes_executed)}")
    print(f"Artifacts Created: {len(result.artifacts)}")
    
    if result.errors:
        print(f"Errors: {len(result.errors)}")
        for error in result.errors:
            print(f"  - {error}")
    
    print(f"\nSummary: {result.summary}")
    print("="*60)


async def demo_admin_workflow():
    """Demo an administrative workflow"""
    
    logger = get_logger(__name__)
    
    # Initialize components  
    mcp_manager = MCPManager()
    planner = TaskGraphPlanner(mcp_manager)
    
    # Create an admin task
    task_spec = TaskSpec(
        task_id="demo_admin_001",
        goal="Process receipt for conference registration and submit reimbursement",
        owner="demo_user",
        priority=Priority.NORMAL,
        runlevel=RunLevel.DRY_RUN,
        tags=["admin", "receipt", "reimbursement", "demo"]
    )
    
    logger.info("Starting admin workflow demo...")
    logger.info(f"Task: {task_spec.goal}")
    
    # Execute the task
    result = await planner.execute_task(task_spec)
    
    # Display results
    print("\n" + "="*60)
    print("ADMIN WORKFLOW RESULTS")
    print("="*60)
    print(f"Task ID: {result.task_id}")
    print(f"Status: {result.status}")
    print(f"Execution Time: {result.execution_time:.2f} seconds")
    print(f"Nodes Executed: {', '.join(result.nodes_executed)}")
    print(f"Artifacts Created: {len(result.artifacts)}")
    
    if result.errors:
        print(f"Errors: {len(result.errors)}")
        for error in result.errors:
            print(f"  - {error}")
    
    print(f"\nSummary: {result.summary}")
    print("="*60)


async def demo_natural_language_parsing():
    """Demo natural language task creation"""
    
    logger = get_logger(__name__)
    
    # Initialize components
    mcp_manager = MCPManager()
    planner = TaskGraphPlanner(mcp_manager)
    
    # Natural language requests
    requests = [
        "Cool down the cryostat to 50 mK and then run a gate sweep",
        "Search for recent papers about topological insulators",
        "Process my travel receipts from the APS conference", 
        "Check the lab status and send me a brief"
    ]
    
    print("\n" + "="*60)
    print("NATURAL LANGUAGE TASK CREATION")
    print("="*60)
    
    for i, request in enumerate(requests, 1):
        print(f"\n{i}. Request: '{request}'")
        
        # Create TaskSpec from natural language
        task_spec = await planner.create_task_from_request(
            user_request=request,
            owner="demo_user", 
            runlevel=RunLevel.DRY_RUN
        )
        
        print(f"   Generated Task ID: {task_spec.task_id}")
        print(f"   Goal: {task_spec.goal}")
        print(f"   Tags: {', '.join(task_spec.tags)}")
        print(f"   Priority: {task_spec.priority}")
        print(f"   Runlevel: {task_spec.runlevel}")
    
    print("="*60)


async def main():
    """Run all demos"""
    
    print("LangGraph Task Planner Demo")
    print("============================")
    print("Demonstrating the new LangGraph-based agent orchestration system")
    print()
    
    try:
        # Demo natural language parsing
        await demo_natural_language_parsing()
        
        # Demo different workflow types
        await demo_cooldown_task()
        await demo_arxiv_research() 
        await demo_admin_workflow()
        
        print("\n✅ All demos completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Ensure examples directory exists
    os.makedirs("examples", exist_ok=True)
    
    # Run the demo
    asyncio.run(main())