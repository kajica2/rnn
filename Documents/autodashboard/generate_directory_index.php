<?php
/**
 * generate_directory_index.php
 *
 * Recursively generates index.html files for all subdirectories.
 * Each page lists subfolders and files with links, includes meta tags,
 * and is ready for deployment to GitHub Pages.
 *
 * Usage:
 *   php generate_directory_index.php
 *
 * The script will create/overwrite index.html in every directory it finds,
 * excluding hidden/system items (like .git, .github, this script itself).
 */

// --- Configuration ---
$ignoreList = [
    '.', '..',
    '.git', '.github', '.svn',             // version control
    'node_modules', 'vendor',              // dependency folders
    basename(__FILE__),                    // this script
    'CNAME', 'README.md', 'LICENSE',       // common repo files
];
$ignoreExtensions = ['php'];              // file extensions to skip (case‑insensitive)
$siteName = 'My Project';                 // default site name (used in <title>)
$metaDescription = 'Directory listing generated automatically.';

// --- Helper functions ---

/**
 * Recursively create index.html in $dir and its subdirectories.
 */
function generateIndexes(string $dir, string $rootDir, array $ignoreList, array $ignoreExtensions, string $siteName, string $metaDescription): void
{
    $dir = realpath($dir);
    if ($dir === false || !is_dir($dir)) {
        return;
    }

    // Collect entries
    $entries = scandir($dir);
    if ($entries === false) {
        return;
    }

    $folders = [];
    $files   = [];

    foreach ($entries as $entry) {
        if (in_array($entry, $ignoreList, true)) {
            continue;
        }

        $fullPath = $dir . DIRECTORY_SEPARATOR . $entry;

        // Skip files with ignored extensions
        $ext = strtolower(pathinfo($entry, PATHINFO_EXTENSION));
        if (is_file($fullPath) && in_array($ext, $ignoreExtensions, true)) {
            continue;
        }

        // Determine type
        if (is_dir($fullPath)) {
            $folders[] = $entry;
        } elseif (is_file($fullPath)) {
            $files[] = $entry;
        }
    }

    // Sort: case‑insensitive alphabetical
    natcasesort($folders);
    natcasesort($files);

    // Build relative path from root for breadcrumb / title
    $relativePath = str_replace('\\', '/', substr($dir, strlen($rootDir)));
    $relativePath = $relativePath === '' ? '/' : '/' . trim($relativePath, '/') . '/';

    // Title and meta
    $pageTitle = ($relativePath === '/') ? $siteName : 'Index of ' . $relativePath;
    $pageDescription = $metaDescription . ' Path: ' . $relativePath;

    // Generate HTML
    $html = buildHtml($pageTitle, $pageDescription, $relativePath, $folders, $files);

    // Write index.html
    $indexFile = $dir . DIRECTORY_SEPARATOR . 'index.html';
    file_put_contents($indexFile, $html);
    echo "Generated: $indexFile\n";

    // Recurse into sub‑folders
    foreach ($folders as $folder) {
        $subDir = $dir . DIRECTORY_SEPARATOR . $folder;
        generateIndexes($subDir, $rootDir, $ignoreList, $ignoreExtensions, $siteName, $metaDescription);
    }
}

/**
 * Build the complete HTML page.
 */
function buildHtml(string $title, string $description, string $relativePath, array $folders, array $files): string
{
    // Parent directory link (unless we are at the root of the generated site)
    $parentLink = '';
    if ($relativePath !== '/') {
        $parentLink = '<p><a href="../">⬆ Parent Directory</a></p>';
    }

    // Build folder list
    $folderList = '';
    if (!empty($folders)) {
        $folderList .= '<h2>Directories</h2><ul>';
        foreach ($folders as $folder) {
            $folderList .= '<li>📁 <a href="' . htmlspecialchars($folder) . '/">' . htmlspecialchars($folder) . '/</a></li>';
        }
        $folderList .= '</ul>';
    }

    // Build file list (with file size for common types)
    $fileList = '';
    if (!empty($files)) {
        $fileList .= '<h2>Files</h2><ul>';
        foreach ($files as $file) {
            $filePath = getcwd() . $relativePath . $file; // not used here, but needed for size
            // Since we are writing to disk, we need the absolute path to compute size
            // We'll compute sizes later inside generateIndexes and pass them, or use a separate array.
            // For simplicity, we'll display the file name only; size can be added if desired.
            $fileList .= '<li>📄 <a href="' . htmlspecialchars($file) . '">' . htmlspecialchars($file) . '</a></li>';
        }
        $fileList .= '</ul>';
    }

    // If nothing to list
    if (empty($folders) && empty($files)) {
        $folderList = '<p>This directory is empty.</p>';
    }

    $html = <<<HTML
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{$title}</title>
    <meta name="description" content="{$description}">
    <meta name="robots" content="noindex, follow">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 800px; margin: 2em auto; padding: 0 1em; line-height: 1.6; color: #333; background: #f9f9f9; }
        h1 { border-bottom: 1px solid #ddd; padding-bottom: 0.3em; }
        ul { list-style: none; padding-left: 0; }
        li { margin: 0.3em 0; }
        a { color: #0366d6; text-decoration: none; }
        a:hover { text-decoration: underline; }
        footer { margin-top: 2em; font-size: 0.9em; color: #666; border-top: 1px solid #ddd; padding-top: 1em; }
    </style>
</head>
<body>
    <h1>Index of {$relativePath}</h1>
    {$parentLink}
    {$folderList}
    {$fileList}
    <footer>
        <p>Generated automatically. <a href="https://github.com">Hosted on GitHub Pages</a>.</p>
    </footer>
</body>
</html>
HTML;
    return $html;
}

// --- Main execution ---
$rootDir = realpath(__DIR__);
if ($rootDir === false) {
    die("Error: Unable to resolve script directory.\n");
}

generateIndexes($rootDir, $rootDir, $ignoreList, $ignoreExtensions, $siteName, $metaDescription);
echo "All index.html files generated.\n";
