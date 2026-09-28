import hashlib,json,struct,zlib,unittest
from test_assets import ROOT,validator

def rgba(path):
    data=path.read_bytes();offset=8;compressed=b''
    while offset<len(data):
        n=struct.unpack('>I',data[offset:offset+4])[0];kind=data[offset+4:offset+8]
        if kind==b'IDAT':compressed+=data[offset+8:offset+8+n]
        offset+=n+12
    raw=zlib.decompress(compressed);previous=bytearray(1024);result=bytearray()
    for start in range(0,len(raw),1025):
        mode=raw[start];row=bytearray(raw[start+1:start+1025])
        for i in range(1024):
            a=row[i-4] if i>=4 else 0;b=previous[i];c=previous[i-4] if i>=4 else 0
            p=a+b-c;dist=[abs(p-a),abs(p-b),abs(p-c)]
            predictor=[0,a,b,(a+b)//2,(a,b,c)[dist.index(min(dist))]][mode]
            row[i]=(row[i]+predictor)&255
        result.extend(row);previous=row
    return bytes(result)

class MoaBlinkMeasuredV3(unittest.TestCase):
    def test_bytes_alpha_safe_regions_and_registration(self):
        m=json.loads((ROOT/'docs/evidence/moa-blink-v3/source-manifest.json').read_text());root=ROOT/'public/assets/creatures/moa/stage01'
        self.assertEqual((m['character'],m['animation']),('MOA','BLINK_V3_MEASURED'))
        self.assertEqual(m['safe_regions'],['LEFT x190..213 y136..165','RIGHT x228..238 y136..159'])
        base=rgba(root/'base.png');centers=[];bottoms=[]
        self.assertEqual(len(m['frames']),3)
        for i,f in enumerate(m['frames']):
            self.assertEqual(f['file'],f'blink_{i+1:02}.png');p=root/f'blink/blink_{i:02}.png';bounds=[]
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),f['sha256']);self.assertEqual(validator.png_errors(p,True,bounds),[])
            pixels=rgba(p);self.assertEqual(pixels[3::4],base[3::4])
            for y in range(256):
                for x in range(256):
                    if not (190<=x<=213 and 136<=y<=165 or 228<=x<=238 and 136<=y<=159):
                        j=(y*256+x)*4;self.assertEqual(pixels[j:j+3],base[j:j+3],(i,x,y))
            centers.append((bounds[0]+bounds[2]+1)/2);bottoms.append(bounds[3]+1)
            self.assertEqual(centers[-1],f['center_x']);self.assertEqual(bottoms[-1],f['bottom'])
        self.assertEqual(max(centers)-min(centers),0);self.assertEqual(max(bottoms)-min(bottoms),0)
        self.assertEqual((root/'blink/blink_00.png').read_bytes(),(root/'blink/blink_02.png').read_bytes())
