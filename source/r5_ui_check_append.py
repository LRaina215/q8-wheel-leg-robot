from pathlib import Path
p=Path('r5_preview.cjs');s=p.read_text(encoding='utf-8-sig').replace("await page.check('#wire');","await page.selectOption('#pairs','1');assert.match(await page.locator('#detail').innerText(),/6.5/);await page.selectOption('#pairs','4');assert.match(await page.locator('#detail').innerText(),/W74/);await page.selectOption('#pairs','');await page.selectOption('#pick','Deck_1');await page.check('#wire');")
p.write_text(s,encoding='utf8')

