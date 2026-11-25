param([string]$Query,[string]$OutputFile,[switch]$ReadOnly)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
$u=[System.Windows.Automation.AutomationElement]
$ts=[System.Windows.Automation.TreeScope]
$ct=[System.Windows.Automation.ControlType]
function Cond($prop,$v){New-Object System.Windows.Automation.PropertyCondition($prop,$v)}
function Get-Tab {
    $win=$u::RootElement.FindAll($ts::Children,(Cond $u::ClassNameProperty 'Chrome_WidgetWin_1')) | Where-Object {$_.Current.Name -in @('ChatGPT','Codex')} | Select-Object -First 1
    if(!$win){throw 'Codex window missing'}
    $docs=$win.FindAll($ts::Descendants,(Cond $u::ControlTypeProperty $ct::Document))
    $docs | Where-Object {$_.Current.Name -like '*淘宝搜索*' -and !$_.Current.IsOffscreen} | Select-Object -Last 1
}
function Cards($doc){
  $items=$doc.FindAll($ts::Descendants,(Cond $u::ControlTypeProperty $ct::Hyperlink))
  foreach($a in $items){
    $url=$a.GetCurrentPropertyValue([System.Windows.Automation.ValuePattern]::ValueProperty) -as [string]
    if($url -match '^https://(item.taobao.com|detail.tmall.com)/item.htm\?' -and $a.Current.Name.Length -gt 10){
      $uri=[uri]$url;$id=[regex]::Match($uri.Query,'[?&]id=([0-9]+)').Groups[1].Value
      $sku=[regex]::Match($uri.Query,'[?&]skuId=([0-9]+)').Groups[1].Value
      $link="https://$($uri.Host)/item.htm?id=$id";if($sku){$link+="&skuId=$sku"}
      [pscustomobject]@{title=$a.Current.Name;url=$link}
    }
  }
}
$d=Get-Tab;if(!$d){throw 'Taobao search tab missing'}
if(!$ReadOnly){
 $edit=$d.FindFirst($ts::Descendants,(Cond $u::ControlTypeProperty $ct::Edit))
 $edit.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue($Query)
 Start-Sleep -Milliseconds 400
 $btn=$d.FindFirst($ts::Descendants,(New-Object System.Windows.Automation.AndCondition((Cond $u::ControlTypeProperty $ct::Button),(Cond $u::NameProperty '搜索'))))
 $btn.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
}
$cards=@();$label=''
for($t=0;$t -lt 18;$t++){
 Start-Sleep -Milliseconds 550
 $d=Get-Tab;if(!$d){continue};$label=$d.Current.Name
 if(!$label.StartsWith($Query)){continue}
 $shops=$d.FindAll($ts::Descendants,(Cond $u::ControlTypeProperty $ct::Hyperlink))
 $key=$null
 foreach($shop in $shops){$v=[string]$shop.GetCurrentPropertyValue([System.Windows.Automation.ValuePattern]::ValueProperty);if($v -match 'shopSearchKeyword=([^&]+)'){$key=[uri]::UnescapeDataString($Matches[1]);break}}
 if($key -and $key -ne $Query){continue}
 $cards=@(Cards $d);if($cards.Count){break}
}
[pscustomobject]@{query=$Query;page=$label;cards=$cards;observed=(Get-Date).ToString('s')}|ConvertTo-Json -Depth 4|Set-Content -Encoding utf8 $OutputFile
"$Query $label $($cards.Count)"

