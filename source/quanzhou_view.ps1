param([string]$Match='铨洲',[switch]$Details)
Add-Type -AssemblyName UIAutomationClient
$u=[System.Windows.Automation.AutomationElement];$ts=[System.Windows.Automation.TreeScope];$ct=[System.Windows.Automation.ControlType]
function pc($k,$v){New-Object System.Windows.Automation.PropertyCondition($k,$v)}
$w=$u::RootElement.FindAll($ts::Children,(pc $u::ClassNameProperty 'Chrome_WidgetWin_1'))|Where-Object {$_.Current.Name -in @('ChatGPT','Codex')}|Select -First 1
$ds=$w.FindAll($ts::Descendants,(pc $u::ControlTypeProperty $ct::Document));$d=$ds|Where-Object {$_.Current.Name -match $Match}|Select -Last 1
if(!$d){$ds|ForEach-Object {$_.Current.Name};exit}
$els=$d.FindAll($ts::Descendants,[System.Windows.Automation.Condition]::TrueCondition)
if($Details){$els|ForEach-Object {$n=$_.Current.Name;if($n -match '设计|打样|加工|上传|文件|标准|权益|会员|报价|仿真|预选|车铣|厚度|孔|STEP|材料|活动|规格|限制|价格|夹持|NG|长度'){if($n.Length -gt 260){$n=$n.Substring(0,260)};"$($_.Current.ControlType.ProgrammaticName) $n"}}}

