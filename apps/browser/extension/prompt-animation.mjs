// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Paint-only rolling letters, matching the native composer's pending/settling phases.
// Never put animation characters into the draft or a model request.
export function startLetterRoll(input){
  const doc=input.ownerDocument,win=doc.defaultView,preview=doc.createElement('div')
  preview.className='prompt-letter-preview';preview.setAttribute('aria-hidden','true')
  let timer=null,finish=null,stopped=false
  const sync=()=>{
    const style=win.getComputedStyle(input)
    for(const key of ['font','lineHeight','padding','borderWidth','borderRadius','letterSpacing','textAlign','tabSize'])preview.style[key]=style[key]
    preview.scrollTop=input.scrollTop;preview.scrollLeft=input.scrollLeft
  }
  const render=text=>{
    const fragment=doc.createDocumentFragment();let index=0
    // Keep words together as in the textarea; oversized words may still wrap.
    for(const token of text.slice(0,8000).split(/(\s+)/u)){
      if(!token)continue
      if(/^\s+$/u.test(token)){fragment.append(doc.createTextNode(token));continue}
      const word=doc.createElement('span');word.className='prompt-letter-word'
      for(const char of token){
        const i=index++
        if(!/[a-z0-9]/i.test(char)){word.append(doc.createTextNode(char));continue}
        const cell=doc.createElement('span'),original=doc.createElement('span'),wheel=doc.createElement('span')
        cell.className='prompt-letter-cell';original.className='prompt-letter-original';wheel.className='prompt-letter-wheel'
        // Desktop advances 7–9.6 letters/second. This CSS loop travels two
        // letter heights, so its duration is two divided by that same rate.
        const rate=7+(i%5)*.65
        cell.style.setProperty('--roll-speed',`${2/rate}s`)
        cell.style.setProperty('--roll-delay',`${-i*.71/rate}s`)
        cell.style.setProperty('--settle-delay',`${(.12+.78*(i*37%101)/100)*680}ms`)
        original.textContent=char
        const alphabet=/[0-9]/.test(char)?'0123456789':'abcdefghijklmnopqrstuvwxyz'
        for(const letter of [char,alphabet[i*13%alphabet.length],char]){const span=doc.createElement('span');span.textContent=letter;wheel.append(span)}
        cell.append(original,wheel);word.append(cell)
      }
      fragment.append(word)
    }
    preview.replaceChildren(fragment);sync()
  }
  input.after(preview);input.classList.add('prompt-improving');input.setAttribute('aria-busy','true')
  render(input.value)
  input.addEventListener('scroll',sync);win.addEventListener('resize',sync)
  const observer=win.ResizeObserver?new win.ResizeObserver(sync):null;observer?.observe(input)
  return {
    settle(text){
      if(stopped)return Promise.resolve(false)
      render(text);preview.classList.add('settling')
      return new Promise(resolve=>{finish=resolve;timer=win.setTimeout(()=>{finish=null;resolve(true)},win.matchMedia?.('(prefers-reduced-motion: reduce)').matches?0:700)})
    },
    stop(){
      if(stopped)return
      stopped=true;win.clearTimeout(timer);finish?.(false);finish=null
      observer?.disconnect();input.removeEventListener('scroll',sync);win.removeEventListener('resize',sync)
      preview.remove();input.classList.remove('prompt-improving');input.removeAttribute('aria-busy')
    },
  }
}
