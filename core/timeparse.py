import re
UNITS={'s':1,'m':60,'h':3600,'d':86400,'w':604800}
def parse_duration(value:str,max_seconds:int|None=None)->int:
    value=value.strip().lower(); total=0; pos=0
    for m in re.finditer(r'(\d+)\s*([smhdw])',value):
        if m.start()!=pos and value[pos:m.start()].strip(): raise ValueError('Ungültige Dauer')
        total+=int(m.group(1))*UNITS[m.group(2)]; pos=m.end()
    if not total or value[pos:].strip(): raise ValueError('Beispiel: 30m, 2h, 7d')
    if max_seconds and total>max_seconds: raise ValueError('Dauer ist zu lang')
    return total

def human(seconds:int)->str:
    parts=[]
    for label,size in [('w',604800),('d',86400),('h',3600),('m',60),('s',1)]:
        q,seconds=divmod(seconds,size)
        if q: parts.append(f'{q}{label}')
    return ' '.join(parts) or '0s'
