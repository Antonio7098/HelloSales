#!/usr/bin/env python3
"""
Automated migration script for stages to ISP interfaces and error handling.

Usage:
    python scripts/migrate_stages.py <stage_file.py>
"""

import re
import sys
from pathlib import Path


def migrate_stages_file(file_path: Path) -> str:
    """Migrate a stages file to use ISP interfaces and consistent error handling."""

    with open(file_path) as f:
        content = f.read()

    original_content = content

    # 1. Update imports to add new interfaces
    new_imports = '''from app.ai.substrate.stages.context import PipelineContext, Stage, StageResult
from app.ai.substrate.pipeline.interfaces import DependentStage, ConditionalStage, ObservableStage
from app.ai.substrate.pipeline.stage_errors import StageRunner'''

    old_import_pattern = r'from app\.ai\.substrate\.pipeline\.context import PipelineContext, Stage, StageResult'
    content = re.sub(old_import_pattern, new_imports, content)

    # 2. Pattern for stages with __init__ that accept ports (DependentStage)
    # Match: class XxxStage(Stage):
    #        name = "xxx"
    #        def __init__(self, xxx_port: ... = None) -> None:
    #    Pattern for stages with __init__ that accept ports (DependentStage)

    # 3. Pattern for ObservableStage (stages that emit events via record_stage_event)
    # We'll add ObservableStage to stages that use ctx.record_stage_event

    # 4. Pattern for ConditionalStage (stages that set ctx.data["skip_xxx"])
    # We'll add ConditionalStage to stages that set skip flags

    # Let's update stages one by one with a more targeted approach

    # Map of stage names to their appropriate interfaces
    stage_interfaces = {
        'InputStage': '(Stage, ObservableStage)',
        'EnricherPrefetchStage': '(Stage, DependentStage, ObservableStage)',
        'TriageStage': '(Stage, DependentStage, ConditionalStage, ObservableStage)',
        'SkillsContextStage': '(Stage, DependentStage, ObservableStage)',
        'ChatContextBuildStage': '(Stage, DependentStage, ObservableStage)',
        'PolicyStage': '(Stage, DependentStage, ObservableStage)',
        'PostLlmPolicyStage': '(Stage, DependentStage, ObservableStage)',
        'GuardrailsStage': '(Stage, DependentStage, ObservableStage)',
        'ChatLlmStreamStage': '(Stage, DependentStage, ObservableStage)',
        'ChatPersistStage': '(Stage, DependentStage, ObservableStage)',
        'AssessmentStage': '(Stage, DependentStage, ObservableStage)',
        'ChatEmitCompleteStage': '(Stage, ObservableStage)',
        'ValidationStage': '(Stage, DependentStage, ObservableStage)',
    }

    # Update class definitions to add interfaces
    for stage_name, interfaces in stage_interfaces.items():
        # Match class definition with optional docstring
        pattern = rf'(@register_stage\(\))\nclass {stage_name}\(Stage\):'
        replacement = rf'\1\nclass {stage_name}{interfaces}:'
        content = re.sub(pattern, replacement, content)

        # Also match without decorator
        pattern2 = rf'class {stage_name}\(Stage\):'
        if f'class {stage_name}{interfaces}' not in content:
            replacement2 = f'class {stage_name}{interfaces}:'
            content = re.sub(pattern2, replacement2, content)

    # 5. Update stages to use StageRunner for error handling
    # Pattern for simple stages - replace try/except with StageRunner

    def replace_with_stage_runner(match):
        """Replace try/except block with StageRunner pattern."""
        _class_name = match.group(1)
        body = match.group(2)

        # Extract the actual work logic (everything before the try block)
        return f'''    async def run(self, ctx: PipelineContext) -> StageResult:
        runner = StageRunner(stage_name=self.name, ctx=ctx)

        def _do_work() -> dict:
            # Stage logic here
            {body.strip()}

        return await runner.run(run_fn=_do_work)'''

    # Save the migrated content
    with open(file_path, 'w') as f:
        f.write(content)

    if content != original_content:
        print(f"Migrated: {file_path}")
        return "modified"
    else:
        print(f"No changes needed: {file_path}")
        return "unchanged"


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        # Migrate all known stage files
        stage_files = [
            Path('/home/antonio/programming/eloquence-ui-tweaks/backend/app/domains/chat/stages.py'),
            Path('/home/antonio/programming/eloquence-ui-tweaks/backend/app/domains/chat/stages/validation.py'),
            Path('/home/antonio/programming/eloquence-ui-tweaks/backend/app/domains/voice/stages/__init__.py'),
            Path('/home/antonio/programming/eloquence-ui-tweaks/backend/app/domains/voice/stages/pipeline.py'),
            Path('/home/antonio/programming/eloquence-ui-tweaks/backend/app/domains/voice/stages/streaming_tts.py'),
            Path('/home/antonio/programming/eloquence-ui-tweaks/backend/app/domains/voice/stages/streaming_llm.py'),
        ]

        for file_path in stage_files:
            if file_path.exists():
                migrate_stages_file(file_path)
            else:
                print(f"File not found: {file_path}")
    else:
        # Migrate specific file
        file_path = Path(sys.argv[1])
        if file_path.exists():
            migrate_stages_file(file_path)
        else:
            print(f"File not found: {file_path}")
            sys.exit(1)


if __name__ == '__main__':
    main()
