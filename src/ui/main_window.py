"""
Main window for Bambu Filament Profile Generator
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Optional, List

from src.generator.profile_builder import ProfileBuilder
from src.scrapers.filament_profiles_scraper import FilamentProfilesScraper
from src.scrapers.github_scraper import GitHubScraper
from src.data.models import FilamentProfile, ScrapedData
from src.utils.logger import get_logger

logger = get_logger()


class BambuFilamentApp:
    """Main application window"""

    def __init__(self, root: tk.Tk):
        """
        Initialize main window

        Args:
            root: Tkinter root window
        """
        self.root = root
        self.root.title("Bambu Filament Profile Generator")
        self.root.geometry("800x600")

        # Apply DOS-style theme
        self._apply_dos_theme()

        # Initialize builder and scrapers
        self.profile_builder = ProfileBuilder()
        self.scrapers = [
            FilamentProfilesScraper(),
            GitHubScraper()
        ]
        self.current_profile: Optional[FilamentProfile] = None
        self.all_scraped_data: List[ScrapedData] = []

        # Build UI
        self._build_ui()

    def _apply_dos_theme(self):
        """Apply DOS-style color scheme"""
        bg_color = "#000000"  # Black background
        fg_color = "#00FF00"  # Green text
        button_bg = "#003300"  # Dark green
        button_fg = "#00FF00"  # Bright green

        self.root.configure(bg=bg_color)

        style = ttk.Style()
        style.theme_use('clam')

        # Configure styles
        style.configure('DOS.TFrame', background=bg_color)
        style.configure('DOS.TLabel', background=bg_color, foreground=fg_color, font=('Courier New', 10))
        style.configure('DOS.TButton', background=button_bg, foreground=button_fg, font=('Courier New', 10, 'bold'))
        style.configure('Title.TLabel', background=bg_color, foreground=fg_color, font=('Courier New', 16, 'bold'))

    def _build_ui(self):
        """Build the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, style='DOS.TFrame', padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="BAMBU FILAMENT PROFILE GENERATOR",
            style='Title.TLabel'
        )
        title_label.pack(pady=(0, 20))

        subtitle = ttk.Label(
            main_frame,
            text="Building Better Profiles... One Filament at a Time",
            style='DOS.TLabel'
        )
        subtitle.pack(pady=(0, 30))

        # Input frame
        input_frame = ttk.Frame(main_frame, style='DOS.TFrame')
        input_frame.pack(fill=tk.X, pady=10)

        # Manufacturer
        ttk.Label(input_frame, text="Manufacturer:", style='DOS.TLabel').grid(row=0, column=0, sticky=tk.W, pady=5)
        self.manufacturer_var = tk.StringVar()
        self.manufacturer_entry = tk.Entry(input_frame, textvariable=self.manufacturer_var, bg='#000000', fg='#00FF00', insertbackground='#00FF00', font=('Courier New', 10))
        self.manufacturer_entry.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=(10, 0))

        # Material Type
        ttk.Label(input_frame, text="Material Type:", style='DOS.TLabel').grid(row=1, column=0, sticky=tk.W, pady=5)
        self.material_var = tk.StringVar(value="PLA")
        material_combo = ttk.Combobox(
            input_frame,
            textvariable=self.material_var,
            values=["PLA", "PETG", "ABS", "TPU"],
            state="readonly",
            font=('Courier New', 10)
        )
        material_combo.grid(row=1, column=1, sticky=tk.EW, pady=5, padx=(10, 0))

        # Material Name
        ttk.Label(input_frame, text="Material Name:", style='DOS.TLabel').grid(row=2, column=0, sticky=tk.W, pady=5)
        self.material_name_var = tk.StringVar()
        self.material_name_entry = tk.Entry(input_frame, textvariable=self.material_name_var, bg='#000000', fg='#00FF00', insertbackground='#00FF00', font=('Courier New', 10))
        self.material_name_entry.grid(row=2, column=1, sticky=tk.EW, pady=5, padx=(10, 0))

        # Color
        ttk.Label(input_frame, text="Color (optional):", style='DOS.TLabel').grid(row=3, column=0, sticky=tk.W, pady=5)
        self.color_var = tk.StringVar()
        self.color_entry = tk.Entry(input_frame, textvariable=self.color_var, bg='#000000', fg='#00FF00', insertbackground='#00FF00', font=('Courier New', 10))
        self.color_entry.grid(row=3, column=1, sticky=tk.EW, pady=5, padx=(10, 0))

        input_frame.columnconfigure(1, weight=1)

        # Button frame
        button_frame = ttk.Frame(main_frame, style='DOS.TFrame')
        button_frame.pack(pady=20)

        self.generate_btn = tk.Button(
            button_frame,
            text="[GENERATE PROFILE]",
            command=self._generate_profile,
            bg='#003300',
            fg='#00FF00',
            font=('Courier New', 10, 'bold'),
            activebackground='#005500',
            activeforeground='#00FF00',
            relief=tk.FLAT,
            padx=20,
            pady=10
        )
        self.generate_btn.pack(side=tk.LEFT, padx=5)

        self.save_btn = tk.Button(
            button_frame,
            text="[SAVE PROFILE]",
            command=self._save_profile,
            bg='#003300',
            fg='#00FF00',
            font=('Courier New', 10, 'bold'),
            activebackground='#005500',
            activeforeground='#00FF00',
            relief=tk.FLAT,
            padx=20,
            pady=10,
            state=tk.DISABLED
        )
        self.save_btn.pack(side=tk.LEFT, padx=5)

        self.import_btn = tk.Button(
            button_frame,
            text="[IMPORT TO BAMBU STUDIO]",
            command=self._import_to_bambu,
            bg='#003300',
            fg='#00FF00',
            font=('Courier New', 10, 'bold'),
            activebackground='#005500',
            activeforeground='#00FF00',
            relief=tk.FLAT,
            padx=20,
            pady=10,
            state=tk.DISABLED
        )
        self.import_btn.pack(side=tk.LEFT, padx=5)

        # Auto-import checkbox
        auto_import_frame = ttk.Frame(main_frame, style='DOS.TFrame')
        auto_import_frame.pack(pady=5)

        self.auto_import_var = tk.BooleanVar(value=False)
        self.auto_import_check = tk.Checkbutton(
            auto_import_frame,
            text="Auto-import to Bambu Studio after generation",
            variable=self.auto_import_var,
            bg='#000000',
            fg='#00FF00',
            selectcolor='#003300',
            activebackground='#000000',
            activeforeground='#00FF00',
            font=('Courier New', 9)
        )
        self.auto_import_check.pack()

        # Output text area
        output_label = ttk.Label(main_frame, text="Generated Profile:", style='DOS.TLabel')
        output_label.pack(anchor=tk.W, pady=(20, 5))

        self.output_text = tk.Text(
            main_frame,
            bg='#000000',
            fg='#00FF00',
            insertbackground='#00FF00',
            font=('Courier New', 9),
            height=15,
            wrap=tk.NONE
        )
        self.output_text.pack(fill=tk.BOTH, expand=True)

        # Scrollbar
        scrollbar = tk.Scrollbar(self.output_text, command=self.output_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.output_text.config(yscrollcommand=scrollbar.set)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, style='DOS.TLabel')
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

    def _generate_profile(self):
        """Generate filament profile"""
        manufacturer = self.manufacturer_var.get().strip()
        material_type = self.material_var.get().strip()
        material_name = self.material_name_var.get().strip()
        color = self.color_var.get().strip()

        if not manufacturer or not material_name:
            messagebox.showerror("Error", "Manufacturer and Material Name are required")
            return

        self.status_var.set("Generating profile...")
        self.root.update()

        try:
            # Create profile name
            profile_name = f"{manufacturer} {material_name}"
            if color:
                profile_name += f" {color}"

            # Search for data from all sources
            logger.info(f"Searching for filament data: {profile_name}")
            scraped_data = []
            for scraper in self.scrapers:
                try:
                    results = scraper.search(
                        manufacturer=manufacturer,
                        material_type=material_type,
                        material_name=material_name,
                        color=color
                    )
                    scraped_data.extend(results)
                    logger.info(f"{scraper.get_source_name()}: Found {len(results)} profiles")
                except Exception as e:
                    logger.error(f"Error with {scraper.get_source_name()}: {e}")

            self.all_scraped_data = scraped_data
            logger.info(f"Total profiles found: {len(scraped_data)}")

            # Build profile
            self.current_profile = self.profile_builder.build_profile(
                name=profile_name,
                material_type=material_type,
                manufacturer=manufacturer,
                scraped_data=scraped_data
            )

            # Display profile JSON
            import json
            profile_json = json.dumps(self.current_profile.to_bambu_json(), indent=2)
            self.output_text.delete('1.0', tk.END)
            self.output_text.insert('1.0', profile_json)

            self.save_btn.config(state=tk.NORMAL)
            self.import_btn.config(state=tk.NORMAL)
            self.status_var.set(f"Profile generated: {profile_name}")

            # Show comparison results if available
            success_msg = f"Profile generated successfully!\n\n"
            success_msg += f"ID: {self.current_profile.filament_id}\n"
            success_msg += f"Sources: {len(scraped_data)} profiles found\n"

            if self.profile_builder.last_comparison:
                comparison = self.profile_builder.last_comparison
                success_msg += f"Conflicts: {len(comparison.conflicts)}\n"
                if comparison.conflicts:
                    success_msg += "\nClick output to see conflict details"

            messagebox.showinfo("Success", success_msg)

            # Show conflicts in output if any
            if self.profile_builder.last_comparison and self.profile_builder.last_comparison.conflicts:
                self._show_comparison_results()

            # Auto-import if enabled
            if self.auto_import_var.get():
                self._import_to_bambu()

        except Exception as e:
            logger.error(f"Failed to generate profile: {e}")
            messagebox.showerror("Error", f"Failed to generate profile:\n{str(e)}")
            self.status_var.set("Error")

    def _save_profile(self):
        """Save current profile to file"""
        if not self.current_profile:
            return

        # Ask for save location
        default_name = f"{self.current_profile.name}.json"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=default_name
        )

        if not file_path:
            return

        try:
            saved_path = self.profile_builder.save_profile(self.current_profile, Path(file_path))
            self.status_var.set(f"Saved to: {saved_path}")
            messagebox.showinfo("Success", f"Profile saved to:\n{saved_path}")

        except Exception as e:
            logger.error(f"Failed to save profile: {e}")
            messagebox.showerror("Error", f"Failed to save profile:\n{str(e)}")

    def _import_to_bambu(self):
        """Import current profile to Bambu Studio"""
        if not self.current_profile:
            return

        self.status_var.set("Importing to Bambu Studio...")
        self.root.update()

        try:
            success, message = self.profile_builder.import_to_bambu_studio(self.current_profile)

            if success:
                self.status_var.set("Imported to Bambu Studio")
                messagebox.showinfo("Success", message)
            else:
                self.status_var.set("Import failed")
                messagebox.showerror("Import Failed", message)

        except Exception as e:
            logger.error(f"Failed to import profile: {e}")
            messagebox.showerror("Error", f"Failed to import profile:\n{str(e)}")
            self.status_var.set("Error")

    def _show_comparison_results(self):
        """Display comparison results and conflicts"""
        if not self.profile_builder.last_comparison:
            return

        comparison = self.profile_builder.last_comparison

        # Prepend comparison info to the output
        import json
        output = "=" * 70 + "\n"
        output += "PROFILE COMPARISON RESULTS\n"
        output += "=" * 70 + "\n\n"
        output += f"Sources analyzed: {comparison.sources_count}\n"
        output += f"Average confidence: {comparison.avg_confidence:.1%}\n"
        output += f"Conflicts found: {len(comparison.conflicts)}\n\n"

        if comparison.conflicts:
            output += "-" * 70 + "\n"
            output += "CONFLICTS AND RESOLUTIONS\n"
            output += "-" * 70 + "\n\n"

            for i, conflict in enumerate(comparison.conflicts, 1):
                output += f"{i}. {conflict.setting_name.upper()}\n"
                output += f"   Recommended: {conflict.recommended_value}\n\n"
                output += f"   Values from sources:\n"
                for value, source, confidence in conflict.values:
                    output += f"     • {value:>5} from {source:<30} (confidence: {confidence:.0%})\n"
                output += f"\n   Resolution: {conflict.reason}\n\n"

        output += "=" * 70 + "\n"
        output += "GENERATED PROFILE JSON\n"
        output += "=" * 70 + "\n\n"

        # Add the JSON
        profile_json = json.dumps(self.current_profile.to_bambu_json(), indent=2)
        output += profile_json

        # Update the output text
        self.output_text.delete('1.0', tk.END)
        self.output_text.insert('1.0', output)
