from pathlib import Path
p=Path(__file__).with_name('r5_pose_reference.py')
s=p.read_text(encoding='utf-8-sig').replace("assert m.ShowConfiguration2(cfg)","m.ShowConfiguration2(cfg);assert asif(asif(m.ConfigurationManager,api.IConfigurationManager).ActiveConfiguration,api.IConfiguration).Name==cfg,cfg")
p.write_text(s,encoding='utf8')
