"""원본 사진 폴더 → 사이트용 사진 3종 + photos.json 생성.

사용: python3 tools/build_photos.py <원본폴더>

- photos/o-… : 원본 화질 그대로(재압축 없음). 위치(GPS) 등 메타데이터는 지우고 회전 정보만 남긴다.
                폴더 이름은 가족 비밀번호에서 만든다(index.html의 fnv와 같은 계산). 비밀번호를 바꾸면 PIN만 고치고 다시 돌린다.
- photos/m    : 화면용, 긴 변 2000px
- photos/t    : 목록용 썸네일, 긴 변 900px
챕터 지정은 아래 CHAPTERS에서 파일 이름으로 한다. 목록에 없는 사진은 'more'로 들어간다.
"""
import io, json, os, re, shutil, sys
import piexif
from PIL import Image, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {'P20260409_140527000', 'IMG_4650', 'IMG_4743', 'IMG_4944',
        'f3dd3e035ebe71e176f667a09ba5e594668cbbc5',  # IMG_2393과 같은 사진(작은 사본)
        'P20260328_120544518', 'IMG_8161',  # 2부 복도 사진: 보정 전 / 1차 보정 → 최종 보정본 IMG_8182만 사용
        'IMG_8170'}  # 2부 무대 사진 보정 전 → 보정본 IMG_8183  # 캡처 모음 / 잘못 올라간 사진 / 신랑·신부만 남기기
# 서사포토그라피 본식스냅(소니 미러리스, 3:2) / 아이폰 스냅(3:4) — 나열 순서도 이 목록대로
SNAP = ['5-0', 'IMG_7762', 'SNAP_bride_bouquet', 'SNAP_couple_seated', 'IMG_7832', 'SNAP_father_walk', 'SNAP_stage',
        'IMG_8125', 'IMG_8145', 'IMG_8146', 'IMG_4888', 'IMG_4887', 'IMG_8110', 'IMG_5214']
IPHONE = [  # 식순대로: 원판 → 신부대기실 → 축가 → 인사·행진 → 2부(핑크 드레스, 구두가 마지막)
    'MAIN_hero', 'IPH_bride_aisle', 'f56109acb6246790059f9f99b158f0edeb178596', 'IMG_8143',            # 원판
    'P20260328_100401018', 'P20260328_100603916', 'IMG_2393', 'IMG_4607', 'IMG_4608',
    'P20260408_094048212', 'P20260408_102426737',
    'IMG_8172', 'IMG_8173', 'IMG_8175', 'IMG_5213',                                               # 신부대기실
    'IMG_8174', 'P20260328_111603777',                                                             # 축가
    'P20260328_112149212', 'P20260328_112340658',                                                  # 인사·행진
    'IMG_5410', 'IMG_8182', 'IMG_8183', 'IMG_8171', 'IMG_8144', 'IMG_8162', 'P20260408_095752458',  # 2부
]
CHAPTERS = {**{k: 'snap' for k in SNAP}, **{k: 'iphone' for k in IPHONE}}
ORDER = SNAP + IPHONE
HERO = 'MAIN_hero'  # 대화창으로 받은 사진(1536px). 원본을 받으면 교체
PIN = '0328'

def fnv(s):
    h = 0x811c9dc5
    for b in s.encode():
        h = ((h ^ b) * 0x01000193) & 0xffffffff
    return format(h, '08x')

FULL = 'o-' + fnv('dir:' + PIN) + fnv('dir2:' + PIN)

def key(name):
    stem = os.path.splitext(name)[0]
    return re.sub(r'_[0-9A-F]{8}-[0-9A-F-]+$', '', stem)  # 아이폰 공유 파일의 긴 꼬리 제거

def slug(k):
    return re.sub(r'[^a-z0-9]+', '-', k.lower()).strip('-')

def strip_full(src, dst):
    """재압축 없이 메타데이터를 전부 걷어낸다: EXIF·XMP(포토샵 작업기록 포함)·IPTC·주석.
    JFIF·색상 프로필(ICC)만 남기고, 회전 정보는 새로 한 칸만 넣는다."""
    try:
        ori = piexif.load(src).get('0th', {}).get(piexif.ImageIFD.Orientation, 1)
    except Exception:
        ori = 1
    data = open(src, 'rb').read()
    out, i = [data[:2]], 2
    while i < len(data):
        m = data[i + 1]
        if m == 0xDA:                                    # 영상 데이터부터 끝까지는 그대로
            end = data.find(b'\xff\xd9', i) + 2               # 첫 이미지 끝까지만 (뒤에 붙은 아이폰 HDR 보조 이미지·메타데이터 제거)
            out.append(data[i:end]); break
        seg = data[i:i + 2 + int.from_bytes(data[i + 2:i + 4], 'big')]
        meta = 0xE1 <= m <= 0xEF or m == 0xFE              # APP1~15, COM
        if not meta or (m == 0xE2 and seg[4:16] == b'ICC_PROFILE\0') or (m == 0xEE and seg[4:9] == b'Adobe'):
            out.append(seg)
        i += len(seg)
    data = b''.join(out)
    if ori != 1:
        o = io.BytesIO()
        piexif.insert(piexif.dump({'0th': {piexif.ImageIFD.Orientation: ori}}), data, o)
        data = o.getvalue()
    open(dst, 'wb').write(data)

def resized(im, edge, dst, q):
    im = im.copy()
    im.thumbnail((edge, edge), Image.LANCZOS)
    im.save(dst, 'JPEG', quality=q, optimize=True, progressive=True)

def main(src_dir):
    for d in (FULL, 'm', 't'):
        os.makedirs(os.path.join(ROOT, 'photos', d), exist_ok=True)
    items = []
    pre_dir = os.path.join(src_dir, 'pre-wedding')            # 웨딩촬영 사진은 이 폴더에 → 'pre' 챕터
    files = [(n, src_dir) for n in sorted(os.listdir(src_dir))]
    if os.path.isdir(pre_dir):
        files += [(n, pre_dir) for n in sorted(os.listdir(pre_dir))]
    for name, folder in files:
        if not name.lower().endswith(('.jpg', '.jpeg')):
            continue
        k = key(name)
        if folder == pre_dir:
            k = 'PRE_' + k
        if k in SKIP:
            continue
        s = slug(k)
        src = os.path.join(folder, name)
        im = ImageOps.exif_transpose(Image.open(src)).convert('RGB')
        strip_full(src, os.path.join(ROOT, 'photos', FULL, s + '.jpg'))
        resized(im, 2000, os.path.join(ROOT, 'photos/m', s + '.jpg'), 85)
        resized(im, 900, os.path.join(ROOT, 'photos/t', s + '.jpg'), 80)
        items.append({'id': s, 'w': im.width, 'h': im.height, 'k': k,
                      'chapter': 'pre' if k.startswith('PRE_') else CHAPTERS.get(k, 'more'), 'hero': k == HERO})
        print(f'{s:24} {im.width}x{im.height} {items[-1]["chapter"]}')
    items.sort(key=lambda it: (ORDER.index(it['k']) if it['k'] in ORDER else len(ORDER), it.pop('k')))
    keep = {it['id'] + '.jpg' for it in items}
    for d in (FULL, 'm', 't'):                                   # 목록에서 빠진 사진 파일 정리
        for f in os.listdir(os.path.join(ROOT, 'photos', d)):
            if f not in keep:
                os.remove(os.path.join(ROOT, 'photos', d, f)); print('removed', d, f)
    json.dump(items, open(os.path.join(ROOT, 'photos/photos.json'), 'w'), ensure_ascii=False, indent=1)
    print(len(items), 'photos')

if __name__ == '__main__':
    main(sys.argv[1])
