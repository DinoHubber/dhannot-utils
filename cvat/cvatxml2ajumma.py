import os
import cv2
import xml.dom.minidom
import argparse

from tqdm import tqdm
from pathlib import Path
from collections import defaultdict

VID_EXTS = ('.mp4', '.avi')
IMG_EXTS = ['.jpg','.jpeg','.png','.tiff','.bmp']
IMG_EXTS = [ str.casefold(x) for x in IMG_EXTS ] 
print(IMG_EXTS)

'''
README for AJUMMA post processing

Naming convention for visualised images: <original image name>_ltrb<box info>.jpg

Note that the box ltrb in the name is the original box annotated, while the visualised box on the visualised image has a buffer around it. 

'''

parser = argparse.ArgumentParser()
parser.add_argument('--xml', type=str, required=True, help='Path to XML file (CVAT IMAGES)')
parser.add_argument('--root', type=str, required=True, help='Path to folder containing images')
parser.add_argument('--out', type=str, required=True, help='Path to folder to output to')
# parser.add_argument('--img_ext', type=str, default='png', help='image extension')
args = parser.parse_args()

box_color = (100,255,0)
box_thickness = 1
# buffer = 0.1
buffer_px = 3

xml_file = args.xml
ignore_frame_str = 'ignore'
classes_map = {"ship": 0, "small_ship": 0, "sampan": 0, "big": 0, "small": 0 }
target_class = ["ship"]
img_root = args.root
out_dir = args.out

doc = xml.dom.minidom.parse(xml_file)

source_name = doc.getElementsByTagName("name")[0].childNodes[0].nodeValue
viz_out_dir = Path(out_dir)/(source_name+'_chipboxed')
if not viz_out_dir.is_dir():
    viz_out_dir.mkdir(parents=True, exist_ok=True)

# image_out_dir = os.path.join(out_dir, 'images')
# if not os.path.isdir(image_out_dir):
#     os.makedirs(image_out_dir)
# viz_out_dir = os.path.join(out_dir, 'viz')
# if not os.path.isdir(viz_out_dir):
#     os.makedirs(viz_out_dir)
# annot_det_out = os.path.join(out_dir, 'annot_det.part.txt')
# annot_det_write = open(annot_det_out,'w')

imgstem2xmlboxes = {}
for image in doc.getElementsByTagName("image"):
    name = image.getAttribute("name")
    stem = Path(name).stem
    imgstem2xmlboxes[stem] = image.getElementsByTagName("box")

ignore_count = 0
image_count = 0
chip_count = 0
for impath in tqdm( [ p for p in Path(img_root).glob('*') if str.casefold(p.suffix) in IMG_EXTS ] ):
    ignore = False
    imstem = impath.stem
    img = cv2.imread(str(impath))
    ih, iw = img.shape[:2]
    viz_frames = []
    if imstem in imgstem2xmlboxes:
        ship_idx = 1
        for box in imgstem2xmlboxes[imstem]:
            viz_frame = img.copy()
            label = box.getAttribute("label")
            if label == ignore_frame_str:
                ignore = True
                break

            if label not in classes_map:
                print('[WARNING] LABEL {} IS NOT FOUND IN CLASSES_MAP'.format(label))
                continue
            cid = classes_map[label]
            l = float(box.getAttribute("xtl")) 
            t = float(box.getAttribute("ytl"))
            r = float(box.getAttribute("xbr"))
            b = float(box.getAttribute("ybr")) 
            
            # buffer_px = buffer * ( r - l )
            box_l = int(max(0, l - buffer_px))
            box_t = int(max(0, t - buffer_px))
            box_r = int(min(iw-1, r + buffer_px))
            box_b = int(min(ih-1, b + buffer_px))

            cv2.rectangle(viz_frame, (box_l,box_t), (box_r,box_b), box_color, box_thickness)
            # cv2.putText(viz_frame, '{}'.format(target_class[cid]), (l+5, b-10), cv2.FONT_HERSHEY_DUPLEX, 1.0, (100,255,0), 1)
            viz_frames.append((viz_frame, imstem, [l,t,r,b]))            
    if ignore:
        ignore_count += 1
    else:
        image_count += 1
        for ship_idx, frameltrb in enumerate(viz_frames):
            frm, imstem, ltrb = frameltrb
            l,t,r,b = ltrb
            imstem = imstem.replace(':','-')
            img_path = viz_out_dir / '{}_ship{}_ltrb{},{},{},{}.jpg'.format(imstem, ship_idx, l, t, r, b)
            cv2.imwrite( str(img_path), frm )
            chip_count += 1
    
    # annot_det_write.write("{}.png".format(stem))
    # for s in annot_det_segs:
    #     annot_det_write.write(s)
    # annot_det_write.write("\n")

    # cv2.imwrite(os.path.join(image_out_dir, '{}.png'.format(stem)), img)
    # cv2.imwrite(os.path.join(viz_out_dir, '{}.jpg'.format(stem)), viz_frame)

# annot_det_write.close()
print('image_count: {}'.format(image_count))
print('chip_count: {}'.format(chip_count))
print('Ignored: {}'.format(ignore_count))

with (Path(out_dir)/'{}_metainfo.txt'.format(source_name)).open('w') as f:
    f.write('{} ships in {} images, {} images ignored'.format(chip_count, image_count, ignore_count))
