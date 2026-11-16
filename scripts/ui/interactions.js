async page => {
 /* AUTH:empty */
 const base='http://127.0.0.1:3197',out='output/ui-review/visual-rhythm',checks=[];page.setDefaultTimeout(12000);
 const check=(ok,name)=>{if(!ok)throw Error(name);checks.push(name);};
 await page.setViewportSize({width:1440,height:900});
 await page.goto(base+'/courses');await page.getByRole('button',{name:'查看实际课程'}).first().click();
 await page.getByRole('dialog').getByRole('heading',{name:'本册尚无已导入课程'}).waitFor();
 await page.keyboard.press('Tab');check(await page.getByRole('dialog').evaluate(e=>e.contains(document.activeElement)),'dialog keyboard focus');
 await page.keyboard.press('Escape');check(await page.getByRole('dialog').count()===0,'catalog modal opens and closes');
 await page.getByRole('navigation',{name:'主导航'}).getByRole('link',{name:'个人设置'}).click();
 await page.getByRole('button',{name:'保存偏好',exact:true}).click();await page.getByRole('status').filter({hasText:'偏好已保存'}).waitFor();check(true,'preferences real save');
 await page.goto(base+'/review');
 const concepts=page.getByRole('region',{name:'跨课程概念卡',exact:true});
 await concepts.getByRole('button',{name:'全部概念卡',exact:true}).click();await concepts.getByRole('heading',{name:'还没有概念复习任务'}).waitFor();
 await concepts.getByRole('button',{name:'刷新概念卡',exact:true}).click();await concepts.getByRole('heading',{name:'还没有概念复习任务'}).waitFor();
 await concepts.getByRole('button',{name:/概念卡到期复习/}).click();await concepts.getByRole('heading',{name:'当前没有到期的概念卡'}).waitFor();check(true,'concept filters and refresh');
 await page.goto(base+'/lesson/demo-01?version=demo-01-v2&tab=text');
 for(const name of ['精听听写','精读词汇','口语跟读','写作','课时测验','课文']) {const tab=page.getByRole('tab',{name,exact:true});await tab.click();await page.waitForFunction(n=>[...document.querySelectorAll('[role=tab]')].some(e=>e.textContent===n&&e.getAttribute('aria-selected')==='true'),name);}
 check(true,'six lesson tabs clickable');
 await page.getByRole('tab',{name:'课文',exact:true}).focus();await page.keyboard.press('ArrowRight');await page.waitForFunction(()=>document.querySelector('#tab-dictation')?.getAttribute('aria-selected')==='true');check(true,'tabs keyboard order');
 await page.getByRole('tab',{name:'课文',exact:true}).click();
 await page.locator('.sentence').last().click();await page.waitForTimeout(200);
 check((await page.locator('.sentence.selected').innerText()).includes('Thank you'),'sentence selection and long list scroll');
 await page.getByRole('button',{name:'内容来源',exact:true}).click();await page.getByRole('dialog').waitFor();await page.keyboard.press('Escape');check(true,'source modal');
 await page.setViewportSize({width:640,height:450});await page.goto(base+'/review');await concepts.getByRole('heading',{name:'当前没有到期的概念卡'}).waitFor();
 check(await page.locator('main').evaluate(e=>e.scrollWidth<=e.clientWidth+1),'200 percent equivalent viewport usable');
 await page.context().storageState({path:'.local/ui-rhythm/empty-auth.json'});
 await page.context().clearCookies();await page.goto(base+'/login');await page.getByRole('button',{name:'注册新账户',exact:true}).click();
 await page.getByLabel('怎么称呼你').fill('UI populated synthetic');await page.getByLabel('邮箱',{exact:true}).fill('ui-populated-r3-20261116@example.invalid');await page.getByLabel('密码').fill('UI-Populated-Only-20261116');
 await page.getByRole('button',{name:'创建账户',exact:true}).click();await page.waitForURL('**/dashboard');check(true,'registration real form submit');
 await page.goto(base+'/lesson/demo-01?version=demo-01-v2&tab=quiz');
 await page.getByRole('button',{name:'开始 / 恢复本轮',exact:true}).click();
 for(const name of ['community garden','On the roof','Them please here.']) {await page.getByRole('radio',{name,exact:true}).check();await page.waitForTimeout(120);}
 await page.getByRole('button',{name:'提交本轮 3 题',exact:true}).click();
 await page.getByRole('heading',{name:/本轮结果：1 \/ 3/}).waitFor();check(true,'real quiz submission generates wrong answer evidence');
 await page.goto(base+'/lesson/teaching-a?version=teaching-a-v1&tab=quiz');
 await page.getByRole('button',{name:'开始 / 恢复本轮',exact:true}).click();
 for(const name of ['Far from the window','Under the notebook','Far away from','Before nine','No']) {await page.getByRole('radio',{name,exact:true}).check();await page.waitForTimeout(120);}
 await page.getByRole('button',{name:'提交本轮 5 题',exact:true}).click();await page.getByRole('heading',{name:/本轮结果：0 \/ 5/}).waitFor();
 await page.goto(base+'/review');await page.locator('.review-card').first().waitFor();
 const allConcepts=page.getByRole('region',{name:'跨课程概念卡',exact:true});
 await allConcepts.locator('.review-card').first().waitFor();check(true,'populated concept cards from real attempts');
 await page.context().storageState({path:'.local/ui-rhythm/populated-auth.json'});
 await page.setViewportSize({width:1440,height:900});await page.screenshot({path:out+'/production-populated-review.png',fullPage:true});
 await page.getByRole('button',{name:'退出登录',exact:true}).click();await page.waitForURL('**/login');check(true,'logout');
 await page.getByLabel('邮箱',{exact:true}).fill('ui-populated-r3-20261116@example.invalid');await page.getByLabel('密码').fill('UI-Populated-Only-20261116');await page.getByRole('button',{name:'登录学习空间',exact:true}).click();await page.waitForURL('**/dashboard');check(true,'login real form submit');
 return {checks};
}
