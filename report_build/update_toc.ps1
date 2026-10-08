# Opens the report in Word, fills in the Table of Contents page numbers, and saves it.
# Word's built-in TOC 1 / TOC 2 styles are tightened so the contents fit on one page.
$docPath = Join-Path (Split-Path $PSScriptRoot -Parent) "ShieldChat_Mini_Project_Report.docx"
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($docPath)
    foreach ($id in -20, -21) {            # wdStyleTOC1, wdStyleTOC2
        $style = $doc.Styles.Item($id)
        $style.ParagraphFormat.SpaceAfter = 1
        $style.ParagraphFormat.SpaceBefore = 0
        $style.Font.Size = 10.5
    }
    foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
    "Pages: " + $doc.ComputeStatistics(2)
    $doc.Save()
    $doc.Close()
} finally { $word.Quit() }
