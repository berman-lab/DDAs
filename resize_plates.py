import sys
from pathlib import Path
from typing import Optional, Union

from PIL import Image
from gooey import Gooey, GooeyParser

from ddas import find_dda_disk, find_petri_dish

# Common image extensions supported by Pillow
VALID_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp'}

def resize_plates(
    input_folder: Union[str, Path],
    output_folder: Union[str, Path],
    max_disk_diameter: int,
    min_plate_diameter: int,
    max_plate_diameter: int,
    target_disk_diameter: Optional[int] = 45,
    max_dev_from_center: int = 100,
    crop_size: Optional[int] = None,
    offset_x: int = 0,
    offset_y: int = 0,
    recursive: bool = False,
):
    input_folder = Path(input_folder)
    output_folder = Path(output_folder)

    if not input_folder.is_dir():
        raise FileNotFoundError(f"Input folder '{input_folder}' does not exist.")

    output_folder.mkdir(parents=True, exist_ok=True)

    if recursive:
        image_files = [
            f for f in input_folder.rglob("*")
            if f.is_file() and f.suffix.lower() in VALID_EXTENSIONS
        ]
    else:
        image_files = [
            f for f in input_folder.iterdir()
            if f.is_file() and f.suffix.lower() in VALID_EXTENSIONS
        ]

    if not image_files:
        raise FileNotFoundError(f"No valid images found in {input_folder}")

    print(f"Found {len(image_files)} images. Locating disks...")

    file_map = {}
    for fpath in image_files:
        try:
            im = Image.open(fpath)
            w, h = im.size
            
            dish_center, _ = find_petri_dish(
                str(fpath),
                min_diameter=min_plate_diameter,
                max_diameter=max_plate_diameter,
            )
            
            dish_offset_x = dish_center[0] - (w // 2)
            dish_offset_y = dish_center[1] - (h // 2)

            # 'radius' returned by find_dda_disk is considered as the diameter as previously established.
            center, disk_radius = find_dda_disk(
                str(fpath),
                max_radius=max_disk_diameter//2,
                max_dev_from_center=max_dev_from_center,
                offset_x=offset_x + dish_offset_x,
                offset_y=offset_y + dish_offset_y,
            )
            disk_diameter = disk_radius * 2
            file_map[fpath] = {'center': center, 'diameter': disk_diameter}
            print(f"Processed {fpath.name}: diameter={disk_diameter}, center={center}")
        except Exception as e:
            print(f"Skipping {fpath.name}: {e}")

    if not file_map:
        raise RuntimeError("No disks were successfully located in any of the images.")

    if target_disk_diameter:
        target_diameter = target_disk_diameter
    else:
        target_diameter = min(info['diameter'] for info in file_map.values())
        print(f"Target disk diameter not set. Using the smallest disk size found: {target_diameter}")

    print(f"Resizing images to target disk diameter: {target_diameter}...")

    # Use fallback property if Pillow version is older and doesn't use `Resampling` Enum
    resample_filter = getattr(Image, 'Resampling', Image).BICUBIC

    for fpath, info in file_map.items():
        try:
            im = Image.open(fpath)
            current_diameter = info['diameter']
            center = info['center']

            scale_factor = target_diameter / current_diameter
            new_size = (int(im.width * scale_factor), int(im.height * scale_factor))
            
            im_rescaled = im.resize(new_size, resample=resample_filter)

            if crop_size:
                scaled_cx = int(center[0] * scale_factor)
                scaled_cy = int(center[1] * scale_factor)
                half_crop = crop_size // 2
                
                left = scaled_cx - half_crop
                top = scaled_cy - half_crop
                right = left + crop_size
                bottom = top + crop_size
                
                im_rescaled = im_rescaled.crop((left, top, right, bottom))

            rel_path = fpath.relative_to(input_folder)
            out_path = output_folder / rel_path.with_suffix('.png')
            out_path.parent.mkdir(parents=True, exist_ok=True)
            im_rescaled.save(out_path, format="PNG")
            print(f"Saved: {out_path}")
        except Exception as e:
            print(f"Error processing {fpath.name}: {e}")

    print("Done!")


@Gooey(program_name="Plate Disk Resizer", default_size=(600, 650))
def main():
    parser = GooeyParser(description="Resize plate photos so that the disks are all of the same target size.")

    parser.add_argument(
        "input_folder",
        widget="DirChooser",
        help="Input folder with plate photos."
    )
    parser.add_argument(
        "output_folder",
        widget="DirChooser",
        help="Output folder for resized images."
    )
    parser.add_argument(
        "max_disk_diameter",
        type=int,
        help="Maximum disk diameter in pixels (mandatory). You should set this to a value slightly larger than the largest disk size in your images to ensure all disks are detected correctly."
    )
    parser.add_argument(
        "min_plate_diameter",
        type=int,
        help="Minimum plate diameter in pixels."
    )
    parser.add_argument(
        "max_plate_diameter",
        type=int,
        help="Maximum plate diameter in pixels."
    )
    parser.add_argument(
        "--target_disk_diameter",
        type=int,
        default=45,
        help="Target disk diameter in pixels. Default is 45.\nClear this field to use the smallest disk size from the existing plates."
    )
    parser.add_argument(
        "--max_dev_from_center",
        type=int,
        default=100,
        help="Maximum deviation of disk from center (pixels)."
    )
    parser.add_argument(
        "--crop_size",
        type=int,
        help="Plate size in pixels for cropping (optional).\nIf set, crops a square around the located disk center AFTER THE RESCALING. " +\
        "For a standard petri dish and disk size, for a target disk diameter of 45 pixels, a crop size of 600 should work well. "
    )
    parser.add_argument(
        "--offset_x",
        type=int,
        default=0,
        help="Horizontal offset relative to the detected plate center to start the disk search."
    )
    parser.add_argument(
        "--offset_y",
        type=int,
        default=0,
        help="Vertical offset relative to the detected plate center to start the disk search."
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="If set, search for images recursively in sub-folders and mirror the folder structure in the output folder."
    )

    args = parser.parse_args()

    try:
        resize_plates(
            input_folder=args.input_folder,
            output_folder=args.output_folder,
            max_disk_diameter=args.max_disk_diameter,
            min_plate_diameter=args.min_plate_diameter,
            max_plate_diameter=args.max_plate_diameter,
            target_disk_diameter=args.target_disk_diameter,
            max_dev_from_center=args.max_dev_from_center,
            crop_size=args.crop_size,
            offset_x=args.offset_x,
            offset_y=args.offset_y,
            recursive=args.recursive
        )
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()