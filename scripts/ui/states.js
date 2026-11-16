async page => {
 /* AUTH:empty */
 const base='http://127.0.0.1:3197',out='output/ui-review/visual-rhythm';
 await page.setViewportSize({width:390,height:844});
 await page.goto(base+'/review');await page.getByRole('heading',{name:'当前没有到期的概念卡'}).waitFor();
 const section=page.getByRole('region',{name:'跨课程概念卡',exact:true});
 await page.route('**/api/v1/concept-reviews/due?*',route=>route.abort('failed'));
 await section.getByRole('button',{name:'刷新概念卡',exact:true}).click();await section.getByRole('alert').waitFor();
 await section.screenshot({path:out+'/after-concepts-error-390.png'});
 await page.unroute('**/api/v1/concept-reviews/due?*');
 await section.getByRole('button',{name:'重新加载',exact:true}).click();await section.getByRole('heading',{name:'当前没有到期的概念卡'}).waitFor();
 let release;const gate=new Promise(resolve=>release=resolve);
 await page.route('**/api/v1/concept-reviews/due?*',async route=>{await gate;await route.continue();});
 await section.getByRole('button',{name:'刷新概念卡',exact:true}).click();await section.getByRole('status').waitFor();
 await section.screenshot({path:out+'/after-concepts-loading-390.png'});release();
 await section.getByRole('heading',{name:'当前没有到期的概念卡'}).waitFor();await page.unroute('**/api/v1/concept-reviews/due?*');
 return {networkFailureVisible:true,realRetryRecovered:true,loadingVisible:true,loadingCompleted:true,apiResponsesModified:false};
}
