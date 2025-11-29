# logger.py - Circular log buffer (RAM-only, ~2KB)
import sys
_buf=None
_max=100
def init(max_lines=100):
 global _buf,_max
 _max=max_lines
 _buf=[]
def log(tag,msg):
 global _buf
 m=f"[{tag}] {msg}"
 print(m)
 try:
  if hasattr(sys.stdout,'flush'):sys.stdout.flush()
 except:pass
 if _buf is not None:
  _buf.append(m)
  if len(_buf)>_max:_buf.pop(0)
def get():
 return '\n'.join(_buf)if _buf else''
def clear():
 global _buf
 if _buf is not None:_buf=[]
