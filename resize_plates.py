import sys
from pathlib import Path

from PIL import Image
from gooey import Gooey, GooeyParser

from ddas import find_dda_disk

# Common image extensions supported by Pillow
VALID_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp'}

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
        help="Horizontal offset relative to the geometric center to start the disk search."
    )
    parser.add_argument(
        "--offset_y",
        type=int,
        default=0,
        help="Vertical offset relative to the geometric center to start the disk search."
    )

    args = parser.parse_args()

    input_folder = Path(args.input_folder)
    output_folder = Path(args.output_folder)

    if not input_folder.is_dir():
        print(f"Error: Input folder '{input_folder}' does not exist.")
        sys.exit(1)

    output_folder.mkdir(parents=True, exist_ok=True)

    image_files = [
        f for f in input_folder.iterdir()
        if f.is_file() and f.suffix.lower() in VALID_EXTENSIONS
    ]

    if not image_files:
        print(f"No valid images found in {input_folder}")
        sys.exit(1)

    print(f"Found {len(image_files)} images. Locating disks...")

    file_map = {}
    for fpath in image_files:
        try:
            # 'radius' returned by find_dda_disk is considered as the diameter as previously established.
            center, disk_radius = find_dda_disk(
                str(fpath),
                max_radius=args.max_disk_diameter//2,
                max_dev_from_center=args.max_dev_from_center,
                offset_x=args.offset_x,
                offset_y=args.offset_y,
                debug_folder="/tmp/"
            )
            disk_diameter = disk_radius * 2
            file_map[fpath] = {'center': center, 'diameter': disk_diameter}
            print(f"Processed {fpath.name}: diameter={disk_diameter}, center={center}")
        except Exception as e:
            print(f"Skipping {fpath.name}: {e}")

    if not file_map:
        print("No disks were successfully located in any of the images.")
        sys.exit(1)

    if args.target_disk_diameter:
        target_diameter = args.target_disk_diameter
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

            if args.crop_size:
                scaled_cx = int(center[0] * scale_factor)
                scaled_cy = int(center[1] * scale_factor)
                half_crop = args.crop_size // 2
                
                left = scaled_cx - half_crop
                top = scaled_cy - half_crop
                right = left + args.crop_size
                bottom = top + args.crop_size
                
                im_rescaled = im_rescaled.crop((left, top, right, bottom))

            out_name = fpath.with_suffix('.png').name
            out_path = output_folder / out_name
            im_rescaled.save(out_path, format="PNG")
            print(f"Saved: {out_path}")
        except Exception as e:
            print(f"Error processing {fpath.name}: {e}")

    print("Done!")

if __name__ == "__main__":
    main()