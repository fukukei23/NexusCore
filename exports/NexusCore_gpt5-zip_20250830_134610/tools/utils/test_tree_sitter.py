# test_tree_sitter.py
from tree_sitter_checker import print_syntax_tree

sample_code = '''
def add(x, y):
    return x + y
'''

print_syntax_tree(sample_code)
