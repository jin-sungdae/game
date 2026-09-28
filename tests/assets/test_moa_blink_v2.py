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

class MoaBlinkV2(unittest.TestCase):
    def test_bytes_alpha_and_registration(self):
        m=json.loads((ROOT/'docs/evidence/moa-blink-v2/source-manifest.json').read_text());root=ROOT/'public/assets/creatures/moa/stage01'
        self.assertEqual((m['character'],m['stage'],m['animation'],m['canvas'],m['source_facing'],m['anchor']),('MOA',1,'BLINK_V2',[256,256],'RIGHT','bottom-center'))
        self.assertEqual(m['sequence'],['half-close','fully-closed','half-open'])
        self.assertEqual(m['registration'],{'base_alpha_bounds':[14,30,244,248],'max_center_x_delta_px':0,'max_bottom_delta_px':0,'alpha_identical_to_base':True,'blink01_equals_blink03_bytes':True})
        base=rgba(root/'base.png');centers=[];bottoms=[]
        self.assertEqual(len(m['frames']),3)
        for i,f in enumerate(m['frames']):
            self.assertEqual(f['file'],f'blink_{i+1:02}.png');p=root/f'blink/blink_{i:02}.png';bounds=[]
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),f['sha256']);self.assertEqual(validator.png_errors(p,True,bounds),[])
            actual=[bounds[0],bounds[1],bounds[2]+1,bounds[3]+1];self.assertEqual(actual,f['alpha_bounds'])
            self.assertEqual(rgba(p)[3::4],base[3::4]);centers.append((actual[0]+actual[2])/2);bottoms.append(actual[3])
            self.assertEqual(centers[-1],f['center_x']);self.assertEqual(bottoms[-1],f['bottom'])
        self.assertEqual(max(centers)-min(centers),0);self.assertEqual(max(bottoms)-min(bottoms),0)
        self.assertEqual((root/'blink/blink_00.png').read_bytes(),(root/'blink/blink_02.png').read_bytes())
