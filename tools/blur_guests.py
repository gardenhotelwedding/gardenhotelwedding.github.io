"""단체 사진에서 하객 얼굴만 동그랗게, 약하게 흐린다. 신랑·신부는 그대로.

사용: python3 tools/blur_guests.py <원본.jpg> <결과.jpg>
FACES는 IMG_4887(휴대폰 불빛 단체컷)을 가로 2000px로 줄였을 때의 [x, y, 너비, 높이].
자동 얼굴 인식(MediaPipe) 결과에서 손·꽃 오검출과 신랑·신부를 빼고, 놓친 얼굴을 손으로 더했다.
"""
import sys
import cv2, numpy as np
from PIL import Image, ImageOps

FACES = [  # 자동 인식
    [218,534,63,63],[907,368,45,45],[401,433,54,54],[998,423,49,49],[1076,368,49,49],[1168,523,44,44],
    [1127,435,51,51],[6,545,70,70],[1400,615,42,42],[219,431,64,64],[65,379,70,70],[1641,465,45,45],
    [447,555,60,60],[1354,520,47,47],[1556,520,49,49],[549,378,48,48],[1373,470,43,43],[678,357,48,48],
    [784,375,60,60],[1253,504,61,61],[1355,352,88,88],[26,473,43,43],[390,332,63,63],[1443,531,48,48],
    [496,390,56,56],[258,403,41,41],[1629,722,55,55],
] + [  # 직접 추가
    [0,432,22,48],[118,330,36,40],[543,438,65,55],[1122,372,40,40],[1200,378,40,42],[1298,388,32,40],
    [1556,442,42,46],[1486,440,40,40],[1496,575,40,40],[1305,585,40,45],
]
STRENGTH = 0.09   # 흐림 세기: 얼굴 너비 대비 (작을수록 약하게)

def main(src, dst):
    im = np.array(ImageOps.exif_transpose(Image.open(src)).convert('RGB')).astype(np.float32)
    H, W = im.shape[:2]; k = W / 2000
    out = im.copy()
    for x, y, w, h in FACES:
        x, y, w, h = x * k, y * k, w * k, h * k
        cx, cy, r = x + w / 2, y + h / 2, max(w, h) * 0.62
        pad = int(r * 1.6)
        x0, y0, x1, y1 = max(0, int(cx - pad)), max(0, int(cy - pad)), min(W, int(cx + pad)), min(H, int(cy + pad))
        patch = im[y0:y1, x0:x1]
        blur = cv2.GaussianBlur(patch, (0, 0), max(w, h) * STRENGTH)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        d = np.hypot(xx - cx, (yy - cy) * 0.9) / r                 # 살짝 세로로 긴 원
        m = np.clip((1.25 - d) / 0.45, 0, 1)[..., None]             # 가장자리는 부드럽게
        out[y0:y1, x0:x1] = out[y0:y1, x0:x1] * (1 - m) + blur * m
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(dst, 'JPEG', quality=95, subsampling=0)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
