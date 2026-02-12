"""
Continuous Improvement Loop for Auto-Learning System.
Created: February 12, 2026

Main orchestration script for self-improvement:
- Run gap scans regularly
- Generate skills for repeated gaps
- Create agents for missing capabilities
- Update rules based on outcomes
- Self-optimize thresholds

Can run as a scheduled task or continuous background service.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ContinuousImprovement")


class ContinuousImprovementLoop:
    """
    Main loop for continuous self-improvement.
    
    Workflow:
    1. Run gap scan to identify issues
    2. Run pattern scan to find automatable patterns
    3. Generate skills for high-frequency patterns
    4. Create agents for capability gaps
    5. Update documentation and registries
    6. Learn from feedback and adjust thresholds
    7. Generate improvement report
    """
    
    def __init__(self, workspace_root: Optional[str] = None):
        self._workspace_root = Path(workspace_root or 
            "c:/Users/admin2/Desktop/MYCOSOFT/CODE/MAS/mycosoft-mas"
        )
        self._scripts_dir = self._workspace_root / "scripts"
        self._cursor_dir = self._workspace_root / ".cursor"
        self._docs_dir = self._workspace_root / "docs"
        self._data_dir = self._workspace_root / "data" / "improvement"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        
        # Thresholds (can be self-optimized)
        self._thresholds = {
            "pattern_min_occurrences": 5,
            "skill_max_generate": 5,
            "gap_high_priority_threshold": 10,
            "learning_sample_min": 10,
            "success_rate_warning": 0.7
        }
        
        self._load_thresholds()
    
    def _load_thresholds(self) -> None:
        """Load thresholds from disk."""
        thresholds_file = self._data_dir / "thresholds.json"
        if thresholds_file.exists():
            try:
                with open(thresholds_file, "r") as f:
                    saved = json.load(f)
                    self._thresholds.update(saved)
            except Exception as e:
                logger.warning(f"Failed to load thresholds: {e}")
    
    def _save_thresholds(self) -> None:
        """Save thresholds to disk."""
        thresholds_file = self._data_dir / "thresholds.json"
        with open(thresholds_file, "w") as f:
            json.dump(self._thresholds, f, indent=2)
    
    def _run_script(
        self,
        script_name: str,
        args: Optional[List[str]] = None,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """Run a script and return result."""
        script_path = self._scripts_dir / script_name
        if not script_path.exists():
            return {"success": False, "error": f"Script not found: {script_name}"}
        
        cmd = ["python", str(script_path)]
        if args:
            cmd.extend(args)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self._workspace_root),
                timeout=timeout
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def run_gap_scan(self) -> Dict[str, Any]:
        """Run gap scan and analyze results."""
        logger.info("Running gap scan...")
        
        result = self._run_script("gap_scan_cursor_background.py")
        if not result["success"]:
            logger.error(f"Gap scan failed: {result.get('error')}")
            return result
        
        # Load and analyze gap report
        gap_report_path = self._cursor_dir / "gap_report_latest.json"
        if gap_report_path.exists():
            with open(gap_report_path, "r") as f:
                gaps = json.load(f)
            
            result["gaps"] = gaps.get("summary", {})
            result["high_priority"] = []
            
            # Identify high-priority gaps
            for repo, repo_gaps in gaps.get("by_repo", {}).items():
                for category, items in repo_gaps.items():
                    if len(items) >= self._thresholds["gap_high_priority_threshold"]:
                        result["high_priority"].append({
                            "repo": repo,
                            "category": category,
                            "count": len(items)
                        })
        
        logger.info(f"Gap scan complete: {result.get('gaps', {})}")
        return result
    
    async def run_pattern_scan(self) -> Dict[str, Any]:
        """Run pattern scan and analyze results."""
        logger.info("Running pattern scan...")
        
        result = self._run_script("pattern_scanner.py")
        if not result["success"]:
            logger.error(f"Pattern scan failed: {result.get('error')}")
            return result
        
        # Load and analyze pattern report
        pattern_report_path = self._cursor_dir / "pattern_scan_report.json"
        if pattern_report_path.exists():
            with open(pattern_report_path, "r") as f:
                patterns = json.load(f)
            
            result["summary"] = patterns.get("summary", {})
            result["suggestions"] = patterns.get("suggestions", [])
            result["top_patterns"] = [
                {"id": p["id"], "occurrences": p["occurrences"]}
                for p in patterns.get("patterns", [])[:10]
            ]
        
        logger.info(f"Pattern scan complete: {result.get('summary', {})}")
        return result
    
    async def generate_skills(self) -> Dict[str, Any]:
        """Generate skills from patterns."""
        logger.info("Generating skills from patterns...")
        
        result = self._run_script("skill_generator.py", [
            "--max-skills", str(self._thresholds["skill_max_generate"]),
            "--min-occurrences", str(self._thresholds["pattern_min_occurrences"])
        ])
        
        if result["success"]:
            logger.info("Skill generation complete")
        else:
            logger.warning(f"Skill generation issues: {result.get('error')}")
        
        return result
    
    async def sync_registries(self) -> Dict[str, Any]:
        """Sync all registries."""
        logger.info("Syncing registries...")
        
        results = {}
        
        # Sync Cursor system
        sync_result = self._run_script("sync_cursor_system.py")
        results["cursor_sync"] = sync_result["success"]
        
        # Build docs manifest
        docs_result = self._run_script("build_docs_manifest.py")
        results["docs_manifest"] = docs_result["success"]
        
        logger.info(f"Registry sync complete: {results}")
        return {"success": all(results.values()), "details": results}
    
    async def analyze_learning(self) -> Dict[str, Any]:
        """Analyze learning feedback for insights."""
        logger.info("Analyzing learning feedback...")
        
        try:
            from mycosoft_mas.services.learning_feedback import get_learning_service
            
            service = get_learning_service()
            summary = service.get_learning_summary()
            suggestions = service.get_improvement_suggestions()
            
            result = {
                "success": True,
                "summary": summary,
                "suggestions": suggestions
            }
            
            # Self-optimize thresholds based on learning
            if summary.get("overall_success_rate", 0) < self._thresholds["success_rate_warning"]:
                logger.warning(f"Low success rate: {summary.get('overall_success_rate'):.0%}")
                # Could adjust thresholds here
            
            return result
        
        except ImportError:
            return {"success": False, "error": "Learning service not available"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def generate_improvement_report(
        self,
        gap_results: Dict[str, Any],
        pattern_results: Dict[str, Any],
        skill_results: Dict[str, Any],
        sync_results: Dict[str, Any],
        learning_results: Dict[str, Any]
    ) -> str:
        """Generate comprehensive improvement report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self._data_dir / f"improvement_report_{timestamp}.json"
        
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "gap_scan": {
                "success": gap_results.get("success", False),
                "summary": gap_results.get("gaps", {}),
                "high_priority": gap_results.get("high_priority", [])
            },
            "pattern_scan": {
                "success": pattern_results.get("success", False),
                "summary": pattern_results.get("summary", {}),
                "suggestions": len(pattern_results.get("suggestions", []))
            },
            "skill_generation": {
                "success": skill_results.get("success", False)
            },
            "registry_sync": sync_results,
            "learning_analysis": {
                "success": learning_results.get("success", False),
                "summary": learning_results.get("summary", {}),
                "suggestions": len(learning_results.get("suggestions", []))
            },
            "thresholds": self._thresholds,
            "next_actions": self._determine_next_actions(
                gap_results, pattern_results, learning_results
            )
        }
        
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Improvement report saved: {report_path}")
        return str(report_path)
    
    def _determine_next_actions(
        self,
        gap_results: Dict[str, Any],
        pattern_results: Dict[str, Any],
        learning_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Determine next actions based on analysis."""
        actions = []
        
        # High-priority gaps
        for gap in gap_results.get("high_priority", []):
            actions.append({
                "type": "address_gap",
                "priority": "high",
                "description": f"Address {gap['count']} {gap['category']} gaps in {gap['repo']}"
            })
        
        # Pattern suggestions
        for suggestion in pattern_results.get("suggestions", [])[:3]:
            actions.append({
                "type": "implement_suggestion",
                "priority": suggestion.get("priority", "medium"),
                "description": suggestion.get("reason", "Pattern-based improvement")
            })
        
        # Learning suggestions
        for suggestion in learning_results.get("suggestions", [])[:3]:
            actions.append({
                "type": suggestion.get("type", "improvement"),
                "priority": "medium",
                "description": suggestion.get("suggestion", "Learning-based improvement")
            })
        
        return actions
    
    async def run_improvement_cycle(self) -> Dict[str, Any]:
        """Run a full improvement cycle."""
        logger.info("=" * 50)
        logger.info("Starting continuous improvement cycle")
        logger.info("=" * 50)
        
        start_time = datetime.now(timezone.utc)
        
        # Step 1: Gap scan
        gap_results = await self.run_gap_scan()
        
        # Step 2: Pattern scan
        pattern_results = await self.run_pattern_scan()
        
        # Step 3: Generate skills
        skill_results = await self.generate_skills()
        
        # Step 4: Sync registries
        sync_results = await self.sync_registries()
        
        # Step 5: Analyze learning
        learning_results = await self.analyze_learning()
        
        # Step 6: Generate report
        report_path = await self.generate_improvement_report(
            gap_results, pattern_results, skill_results,
            sync_results, learning_results
        )
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        logger.info("=" * 50)
        logger.info(f"Improvement cycle complete in {duration:.1f}s")
        logger.info(f"Report: {report_path}")
        logger.info("=" * 50)
        
        return {
            "success": True,
            "duration_seconds": duration,
            "report_path": report_path,
            "next_actions": self._determine_next_actions(
                gap_results, pattern_results, learning_results
            )
        }
    
    async def run_continuous(self, interval_hours: int = 24) -> None:
        """Run continuous improvement loop."""
        logger.info(f"Starting continuous improvement (every {interval_hours}h)")
        
        while True:
            try:
                result = await self.run_improvement_cycle()
                
                if result.get("next_actions"):
                    logger.info(f"Next actions: {len(result['next_actions'])}")
                    for action in result["next_actions"][:3]:
                        logger.info(f"  - [{action['priority']}] {action['description'][:60]}")
                
            except Exception as e:
                logger.error(f"Improvement cycle failed: {e}")
            
            # Wait for next cycle
            await asyncio.sleep(interval_hours * 3600)


def main():
    """Run continuous improvement."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Continuous improvement loop")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=24, help="Hours between cycles")
    parser.add_argument("--gap-scan-only", action="store_true", help="Only run gap scan")
    parser.add_argument("--pattern-scan-only", action="store_true", help="Only run pattern scan")
    
    args = parser.parse_args()
    
    loop = ContinuousImprovementLoop()
    
    if args.gap_scan_only:
        result = asyncio.run(loop.run_gap_scan())
        print(json.dumps(result, indent=2))
    
    elif args.pattern_scan_only:
        result = asyncio.run(loop.run_pattern_scan())
        print(json.dumps(result, indent=2))
    
    elif args.once:
        result = asyncio.run(loop.run_improvement_cycle())
        print("\n=== Improvement Cycle Complete ===")
        print(f"Duration: {result['duration_seconds']:.1f}s")
        print(f"Report: {result['report_path']}")
        
        if result.get("next_actions"):
            print("\nNext Actions:")
            for action in result["next_actions"]:
                print(f"  [{action['priority']}] {action['description']}")
    
    else:
        try:
            asyncio.run(loop.run_continuous(interval_hours=args.interval))
        except KeyboardInterrupt:
            print("\nStopped")


if __name__ == "__main__":
    main()
