async (providedPage) => {
  const identity = {web:'http://127.0.0.1:3198',cardId:'d3d3c982-4bd9-4780-a3ac-1c024a1f9a21'};
  const context=await providedPage.context().browser().newContext({viewport:{width:1440,height:900}});
  const page=await context.newPage();
  const errors=[],responses=[];
  page.on('pageerror',error=>errors.push({type:'pageerror',message:error.message}));
  page.on('requestfailed',request=>errors.push({type:'networkerror',url:request.url(),failure:request.failure()}));
  page.on('response',response=>{if(response.url().includes('/api/v1/'))responses.push({url:response.url(),status:response.status()});});
  try {
    await page.goto(identity.web+'/review');
    await page.getByRole('button',{name:'全部概念卡',exact:true}).click();
    const card=page.locator('.review-card').filter({has:page.getByRole('heading',{name:'bank — financial institution',exact:true})});
    await card.waitFor();
    await card.locator('summary').click();
    await card.getByText('已显示 0/1 条可见').waitFor();
    const clicks=[];
    for(let index=0;index<10;index++) {
      const button=card.getByRole('button',{name:'加载更多来源',exact:true});
      if(!await button.count())break;
      await button.click();
      await card.getByText(/正在读取来源…/).waitFor();
      await card.getByText(/正在读取来源…/).waitFor({state:'detached'});
      clicks.push(index+1);
    }
    await card.getByText('已显示 1/1 条可见').waitFor();
    const restricted=await card.getByText(/内容不可用（课程已撤回或无访问权限）/).count();
    const visibleLinks=await card.getByRole('link',{name:/查看这次练习/}).count();
    const loadMore=await card.getByRole('button',{name:'加载更多来源',exact:true}).count();
    const result={result:restricted===82&&visibleLinks===1&&loadMore===0?'PASS':'FAIL',restricted,visibleLinks,uiCount:restricted+visibleLinks,loadMoreButtons:loadMore,clicks,summary:await card.locator('summary').innerText(),pageErrors:errors,responses};
    await page.screenshot({path:'/Users/wangshiqi/Project/NorthstarEnglish/output/playwright/phase10d-final-r4/sources-fixed.png',fullPage:true});
    return result;
  } finally {await context.close();}
}
