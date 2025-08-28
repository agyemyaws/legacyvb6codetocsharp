"""
Dependency Resolver
Resolves dependencies between VB6 files and determines optimal translation order.
"""

from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict, deque
import logging


class CircularDependencyError(Exception):
    """Raised when circular dependencies are detected"""
    pass


class DependencyResolver:
    """Resolves dependencies and determines translation order"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def resolve_dependencies(self, dependencies: Dict[str, List[str]]) -> List[str]:
        """
        Resolve dependencies and return files in translation order.
        
        Args:
            dependencies: Dict mapping file names to their dependencies
            
        Returns:
            List of file names in dependency order (dependencies first)
            
        Raises:
            CircularDependencyError: If circular dependencies are detected
        """
        # Validate input
        if not dependencies:
            return []
        
        # Build dependency graph
        graph = self._build_dependency_graph(dependencies)
        
        # Check for circular dependencies
        cycles = self._detect_cycles(graph)
        if cycles:
            raise CircularDependencyError(f"Circular dependencies detected: {cycles}")
        
        # Perform topological sort
        sorted_files = self._topological_sort(graph)
        
        self.logger.info(f"Resolved dependencies for {len(sorted_files)} files")
        return sorted_files
    
    def _build_dependency_graph(self, dependencies: Dict[str, List[str]]) -> Dict[str, Set[str]]:
        """Build a dependency graph from the input"""
        graph = defaultdict(set)
        all_files = set(dependencies.keys())
        
        # Add all files to ensure they're in the graph
        for file_name in all_files:
            graph[file_name] = set()
        
        # Add dependencies
        for file_name, deps in dependencies.items():
            for dep in deps:
                # Only include dependencies that exist in our file set
                if dep in all_files:
                    graph[file_name].add(dep)
        
        return dict(graph)
    
    def _detect_cycles(self, graph: Dict[str, Set[str]]) -> List[List[str]]:
        """
        Detect cycles in the dependency graph using DFS.
        
        Returns:
            List of cycles found (each cycle is a list of file names)
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        colors = {node: WHITE for node in graph}
        cycles = []
        path = []
        
        def dfs(node: str) -> bool:
            if colors[node] == GRAY:
                # Found a back edge - cycle detected
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return True
            
            if colors[node] == BLACK:
                return False
            
            colors[node] = GRAY
            path.append(node)
            
            for neighbor in graph[node]:
                if dfs(neighbor):
                    return True
            
            path.pop()
            colors[node] = BLACK
            return False
        
        for node in graph:
            if colors[node] == WHITE:
                dfs(node)
        
        return cycles
    
    def _topological_sort(self, graph: Dict[str, Set[str]]) -> List[str]:
        """
        Perform topological sort using Kahn's algorithm.
        
        Returns:
            List of nodes in topological order
        """
        # Calculate in-degrees
        in_degree = defaultdict(int)
        for node in graph:
            in_degree[node] = 0
        
        for node in graph:
            for neighbor in graph[node]:
                in_degree[neighbor] += 1
        
        # Find nodes with no incoming edges
        queue = deque([node for node in graph if in_degree[node] == 0])
        result = []
        
        while queue:
            node = queue.popleft()
            result.append(node)
            
            # Remove edges from this node
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Check if all nodes were processed (no cycles)
        if len(result) != len(graph):
            remaining = [node for node in graph if node not in result]
            self.logger.warning(f"Some nodes not processed in topological sort: {remaining}")
        
        return result
    
    def analyze_dependency_complexity(self, dependencies: Dict[str, List[str]]) -> Dict[str, any]:
        """
        Analyze the complexity of the dependency graph.
        
        Returns:
            Dictionary with analysis results
        """
        graph = self._build_dependency_graph(dependencies)
        
        # Calculate metrics
        total_files = len(graph)
        total_dependencies = sum(len(deps) for deps in graph.values())
        
        # Find files with no dependencies (leaf nodes)
        leaf_files = [file for file, deps in graph.items() if not deps]
        
        # Find files with no dependents (root nodes)
        dependents = defaultdict(set)
        for file, deps in graph.items():
            for dep in deps:
                dependents[dep].add(file)
        
        root_files = [file for file in graph if not dependents[file]]
        
        # Calculate dependency depth for each file
        depths = self._calculate_depths(graph)
        max_depth = max(depths.values()) if depths else 0
        
        # Find strongly connected components (for cycle analysis)
        sccs = self._find_strongly_connected_components(graph)
        
        return {
            'total_files': total_files,
            'total_dependencies': total_dependencies,
            'average_dependencies_per_file': total_dependencies / total_files if total_files > 0 else 0,
            'leaf_files': leaf_files,
            'root_files': root_files,
            'max_dependency_depth': max_depth,
            'file_depths': depths,
            'strongly_connected_components': sccs,
            'has_cycles': any(len(scc) > 1 for scc in sccs)
        }
    
    def _calculate_depths(self, graph: Dict[str, Set[str]]) -> Dict[str, int]:
        """Calculate the dependency depth for each file"""
        depths = {}
        visited = set()
        
        def dfs_depth(node: str) -> int:
            if node in visited:
                return depths.get(node, 0)
            
            visited.add(node)
            
            if not graph[node]:
                depths[node] = 0
            else:
                max_dep_depth = max(dfs_depth(dep) for dep in graph[node])
                depths[node] = max_dep_depth + 1
            
            return depths[node]
        
        for node in graph:
            if node not in visited:
                dfs_depth(node)
        
        return depths
    
    def _find_strongly_connected_components(self, graph: Dict[str, Set[str]]) -> List[List[str]]:
        """
        Find strongly connected components using Tarjan's algorithm.
        
        Returns:
            List of strongly connected components
        """
        index_counter = [0]
        stack = []
        lowlinks = {}
        index = {}
        on_stack = {}
        sccs = []
        
        def strongconnect(node: str):
            index[node] = index_counter[0]
            lowlinks[node] = index_counter[0]
            index_counter[0] += 1
            stack.append(node)
            on_stack[node] = True
            
            for neighbor in graph[node]:
                if neighbor not in index:
                    strongconnect(neighbor)
                    lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
                elif on_stack.get(neighbor, False):
                    lowlinks[node] = min(lowlinks[node], index[neighbor])
            
            if lowlinks[node] == index[node]:
                component = []
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    component.append(w)
                    if w == node:
                        break
                sccs.append(component)
        
        for node in graph:
            if node not in index:
                strongconnect(node)
        
        return sccs
    
    def suggest_translation_strategies(self, dependencies: Dict[str, List[str]]) -> Dict[str, any]:
        """
        Suggest strategies for handling complex dependency scenarios.
        
        Returns:
            Dictionary with suggested strategies
        """
        analysis = self.analyze_dependency_complexity(dependencies)
        strategies = []
        
        # Strategy for files with no dependencies
        if analysis['leaf_files']:
            strategies.append({
                'type': 'parallel_translation',
                'description': 'Files with no dependencies can be translated in parallel',
                'files': analysis['leaf_files'],
                'priority': 'high'
            })
        
        # Strategy for files with many dependencies
        high_dependency_files = [
            file for file, deps in dependencies.items() 
            if len(deps) > analysis['average_dependencies_per_file'] * 1.5
        ]
        
        if high_dependency_files:
            strategies.append({
                'type': 'late_translation',
                'description': 'Files with many dependencies should be translated later',
                'files': high_dependency_files,
                'priority': 'medium'
            })
        
        # Strategy for cycles
        if analysis['has_cycles']:
            cycle_files = [file for scc in analysis['strongly_connected_components'] 
                          if len(scc) > 1 for file in scc]
            strategies.append({
                'type': 'interface_extraction',
                'description': 'Files in cycles need interface extraction to break dependencies',
                'files': cycle_files,
                'priority': 'critical'
            })
        
        # Strategy for deep dependency chains
        if analysis['max_dependency_depth'] > 5:
            deep_files = [file for file, depth in analysis['file_depths'].items() 
                         if depth > 3]
            strategies.append({
                'type': 'incremental_translation',
                'description': 'Deep dependency chains should be translated incrementally',
                'files': deep_files,
                'priority': 'medium'
            })
        
        return {
            'analysis': analysis,
            'strategies': strategies,
            'recommended_approach': self._recommend_approach(analysis, strategies)
        }
    
    def _recommend_approach(self, analysis: Dict, strategies: List[Dict]) -> str:
        """Recommend the best overall approach based on analysis"""
        if analysis['has_cycles']:
            return "interface_first"  # Extract interfaces first to break cycles
        elif analysis['max_dependency_depth'] > 5:
            return "bottom_up"  # Start with leaf nodes and work up
        elif len(analysis['leaf_files']) > len(analysis['root_files']):
            return "parallel_leaves"  # Start with multiple leaf files in parallel
        else:
            return "standard_topological"  # Standard dependency order
    
    def create_translation_batches(self, dependencies: Dict[str, List[str]], 
                                 batch_size: int = 5) -> List[List[str]]:
        """
        Create batches of files that can be translated together.
        
        Args:
            dependencies: File dependencies
            batch_size: Maximum files per batch
            
        Returns:
            List of batches (each batch is a list of file names)
        """
        try:
            sorted_files = self.resolve_dependencies(dependencies)
        except CircularDependencyError:
            # If there are cycles, use a different strategy
            self.logger.warning("Circular dependencies detected, using alternative batching")
            sorted_files = list(dependencies.keys())
        
        graph = self._build_dependency_graph(dependencies)
        batches = []
        processed = set()
        
        while len(processed) < len(sorted_files):
            current_batch = []
            
            for file in sorted_files:
                if file in processed:
                    continue
                
                # Check if all dependencies are already processed
                if all(dep in processed or dep not in dependencies 
                       for dep in graph[file]):
                    current_batch.append(file)
                    processed.add(file)
                    
                    if len(current_batch) >= batch_size:
                        break
            
            if current_batch:
                batches.append(current_batch)
            else:
                # If no files can be processed, there might be remaining cycles
                remaining = [f for f in sorted_files if f not in processed]
                if remaining:
                    # Add remaining files to a final batch
                    batches.append(remaining[:batch_size])
                    processed.update(remaining[:batch_size])
                break
        
        return batches


def main():
    """Test function for the dependency resolver"""
    import json
    
    # Test data
    test_dependencies = {
        'Form1': ['Module1', 'Class1'],
        'Form2': ['Module1', 'Module2'],
        'Module1': [],
        'Module2': ['Class1'],
        'Class1': [],
        'Class2': ['Class1', 'Module1']
    }
    
    resolver = DependencyResolver()
    
    try:
        # Test dependency resolution
        order = resolver.resolve_dependencies(test_dependencies)
        print("Translation order:", order)
        
        # Test complexity analysis
        analysis = resolver.analyze_dependency_complexity(test_dependencies)
        print("\nDependency Analysis:")
        print(json.dumps(analysis, indent=2, default=str))
        
        # Test translation strategies
        strategies = resolver.suggest_translation_strategies(test_dependencies)
        print("\nTranslation Strategies:")
        print(json.dumps(strategies, indent=2, default=str))
        
        # Test batching
        batches = resolver.create_translation_batches(test_dependencies, batch_size=3)
        print(f"\nTranslation Batches:")
        for i, batch in enumerate(batches):
            print(f"Batch {i+1}: {batch}")
            
    except CircularDependencyError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
