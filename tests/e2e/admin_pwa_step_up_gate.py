"""Pause the native mutation ceremony for cancellation/stale-write browser QA."""


async def install_step_up_gate(page):
    await page.add_init_script("""(()=>{
      const get=navigator.credentials.get.bind(navigator.credentials);
      window.holdStepUp=true;window.stepUpWaiting=false;
      navigator.credentials.get=async options=>{
        if(window.holdStepUp&&options.publicKey?.allowCredentials?.length){
          await new Promise((resolve,reject)=>{
            window.stepUpWaiting=true;
            const finish=error=>{window.stepUpWaiting=false;options.signal?.removeEventListener('abort',abort);error?reject(error):resolve();};
            const abort=()=>finish(new DOMException('Cancelled by test','AbortError'));
            window.finishStepUp=()=>finish();
            window.cancelStepUp=()=>finish(new DOMException('Cancelled by test','NotAllowedError'));
            options.signal?.addEventListener('abort',abort,{once:true});
          });
        }
        return get(options);
      };
    })()""")


async def wait_step_up(page):
    await page.wait_for_function("() => window.stepUpWaiting===true")
    assert await page.locator('[data-action="managementExecute"],[data-action="execute"],[data-action="executeAccess"],.management-comparison').count() == 0


async def finish_step_up(page):
    await page.evaluate("window.finishStepUp()")
