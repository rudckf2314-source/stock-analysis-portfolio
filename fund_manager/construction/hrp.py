"""
HRP (Hierarchical Risk Parity) Portfolio Optimization

HRP는 상관구조 기반의 클러스터링을 통해 "자연스러운" 분산을 달성하는 알고리즘입니다.
전통적인 Mean-Variance 최적화의 표본오차 문제를 회피할 수 있습니다.

Algorithm Steps:
1. Calculate correlation matrix
2. Hierarchical clustering using correlation distance
3. Quasi-diagonalization
4. Recursive bisection for weight allocation

Reference: 
- López de Prado, M. (2016). "Building Diversified Portfolios that Outperform Out of Sample"
"""

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, dendrogram
from scipy.spatial.distance import squareform
from typing import Dict, List, Tuple


class HRPOptimizer:
    """
    Hierarchical Risk Parity Portfolio Optimizer
    """
    
    def __init__(self, returns: pd.DataFrame):
        """
        Initialize HRP optimizer with historical returns.
        
        Args:
            returns: DataFrame of asset returns (dates × assets)
        """
        self.returns = returns
        self.assets = returns.columns.tolist()
        self.cov_matrix = returns.cov()
        self.corr_matrix = returns.corr()
    
    def optimize(self) -> Dict[str, float]:
        """
        Run HRP optimization.
        
        Returns:
            Dictionary of {asset: weight}
        """
        # Step 1: Hierarchical clustering
        link = self._tree_clustering()
        
        # Step 2: Quasi-diagonalization
        sorted_assets = self._quasi_diag(link)
        
        # Step 3: Recursive bisection
        weights = self._recursive_bisection(sorted_assets)
        
        # Normalize to sum to 1
        total = sum(weights.values())
        weights = {k: v / total for k, v in weights.items()}
        
        return weights
    
    def _tree_clustering(self) -> np.ndarray:
        """
        Step 1: Hierarchical clustering based on correlation distance.
        
        Returns:
            Linkage matrix
        """
        # Convert correlation to distance
        # Distance = sqrt(0.5 * (1 - correlation))
        dist_matrix = np.sqrt(0.5 * (1 - self.corr_matrix))
        
        # Convert to condensed distance matrix
        dist_condensed = squareform(dist_matrix)
        
        # Hierarchical clustering (single linkage)
        link = linkage(dist_condensed, method='single')
        
        return link
    
    def _quasi_diag(self, link: np.ndarray) -> List[str]:
        """
        Step 2: Quasi-diagonalization - reorder assets to maximize diagonal.
        
        Args:
            link: Linkage matrix
            
        Returns:
            List of assets in quasi-diagonal order
        """
        # Get the order of assets from hierarchical clustering
        link = link.astype(int)
        sorted_indices = self._get_quasi_diag_order(link, len(self.assets))
        
        sorted_assets = [self.assets[i] for i in sorted_indices]
        
        return sorted_assets
    
    def _get_quasi_diag_order(self, link: np.ndarray, num_assets: int) -> List[int]:
        """
        Helper: Extract quasi-diagonal order from linkage matrix.
        """
        # Traverse the dendrogram to get leaf order
        def get_leaves(link, node, num_assets):
            if node < num_assets:
                return [node]
            else:
                left = int(link[node - num_assets, 0])
                right = int(link[node - num_assets, 1])
                return get_leaves(link, left, num_assets) + get_leaves(link, right, num_assets)
        
        # Root node is the last one
        root = 2 * num_assets - 2
        order = get_leaves(link, root, num_assets)
        
        return order
    
    def _recursive_bisection(self, sorted_assets: List[str]) -> Dict[str, float]:
        """
        Step 3: Recursive bisection to allocate weights.
        
        Args:
            sorted_assets: Assets in quasi-diagonal order
            
        Returns:
            Dictionary of {asset: weight}
        """
        # Initialize all weights to 1
        weights = {asset: 1.0 for asset in sorted_assets}
        
        # Recursive function
        self._bisect_weights(sorted_assets, weights)
        
        return weights
    
    def _bisect_weights(self, assets: List[str], weights: Dict[str, float]):
        """
        Recursive helper for bisection.
        """
        if len(assets) == 1:
            return
        
        # Split into two clusters
        mid = len(assets) // 2
        cluster1 = assets[:mid]
        cluster2 = assets[mid:]
        
        # Calculate cluster variances
        var1 = self._cluster_variance(cluster1)
        var2 = self._cluster_variance(cluster2)
        
        # Allocate weight inversely proportional to variance
        alpha = 1 - var1 / (var1 + var2)
        
        # Update weights
        for asset in cluster1:
            weights[asset] *= alpha
        for asset in cluster2:
            weights[asset] *= (1 - alpha)
        
        # Recurse on both clusters
        self._bisect_weights(cluster1, weights)
        self._bisect_weights(cluster2, weights)
    
    def _cluster_variance(self, assets: List[str]) -> float:
        """
        Calculate variance of a cluster.
        
        Args:
            assets: List of assets in the cluster
            
        Returns:
            Cluster variance
        """
        # Extract covariance sub-matrix
        indices = [self.assets.index(asset) for asset in assets]
        cov_sub = self.cov_matrix.iloc[indices, indices]
        
        # Equal-weighted variance
        n = len(assets)
        w = np.ones(n) / n
        variance = np.dot(w, np.dot(cov_sub.values, w))
        
        return variance


# ============================================================
# Example Usage
# ============================================================

def example_hrp():
    """
    Example: HRP optimization
    """
    # Generate sample returns data
    np.random.seed(42)
    n_assets = 5
    n_days = 252
    
    assets = ['Asset_A', 'Asset_B', 'Asset_C', 'Asset_D', 'Asset_E']
    
    # Simulate correlated returns
    mean_returns = np.array([0.0005, 0.0007, 0.0006, 0.0004, 0.0008])
    cov_matrix = np.array([
        [0.0004, 0.0002, 0.0001, 0.0001, 0.0001],
        [0.0002, 0.0005, 0.0002, 0.0001, 0.0001],
        [0.0001, 0.0002, 0.0003, 0.0001, 0.0001],
        [0.0001, 0.0001, 0.0001, 0.0002, 0.0001],
        [0.0001, 0.0001, 0.0001, 0.0001, 0.0006],
    ])
    
    returns = pd.DataFrame(
        np.random.multivariate_normal(mean_returns, cov_matrix, n_days),
        columns=assets
    )
    
    # Run HRP
    hrp = HRPOptimizer(returns)
    weights = hrp.optimize()
    
    print("HRP Optimized Weights:")
    for asset, weight in weights.items():
        print(f"  {asset}: {weight:.4f} ({weight*100:.2f}%)")
    
    return weights


if __name__ == "__main__":
    example_hrp()
