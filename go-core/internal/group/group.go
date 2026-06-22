package group

import (
	"path/filepath"
	"sort"
)

// ByParentDir groups a list of paths by their immediate parent directory name.
// Returns group names in stable order (first-seen) and a map of group → paths.
func ByParentDir(paths []string) ([]string, map[string][]string) {
	groups := make(map[string][]string)
	var order []string
	seen := make(map[string]bool)

	for _, p := range paths {
		parent := filepath.Base(filepath.Dir(p))
		if !seen[parent] {
			order = append(order, parent)
			seen[parent] = true
		}
		groups[parent] = append(groups[parent], p)
	}

	return order, groups
}

// ByParentDirSorted is like ByParentDir but returns groups sorted alphabetically.
func ByParentDirSorted(paths []string) ([]string, map[string][]string) {
	order, groups := ByParentDir(paths)
	sort.Strings(order)
	return order, groups
}
