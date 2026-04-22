#!/bin/bash
# Debug runner to see where mutmut runs the command

echo "PWD: $(pwd)" >> /tmp/mutmut_runner_debug.log
echo "PYTHONPATH: $PYTHONPATH" >> /tmp/mutmut_runner_debug.log
echo "LS: $(ls -la | head -10)" >> /tmp/mutmut_runner_debug.log
echo "---" >> /tmp/mutmut_runner_debug.log

python -m pytest tests/agents/test_mutation_tester_agent.py --tb=no -q -p no:warnings
