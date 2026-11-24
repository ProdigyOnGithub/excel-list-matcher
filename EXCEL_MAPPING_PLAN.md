# Master Plan & Implementation Checklists: Excel Raw Data to Myntra Template Matcher

A comprehensive development roadmap, edge-case catalog, fallback matrix, and verification checklist for building the **Excel Matcher** (`MyntraMatching`) using Python, `pandas`, and `openpyxl`.

---

## 1. File & Environment Pre-Flight Checklist

Ensure the environment, source files, and dependencies are sound before executing data operations.

- [ ] **Python Environment & Library Check**
  - [ ] Verify Python version $\ge$ 3.10.
  - [ ] Ensure `pandas` is installed for vectorised transformations.
  - [ ] Ensure `openpyxl` is installed to parse and write `.xlsx` files without losing header hierarchies.
- [ ] **Source File Presence & Validation**
  - [ ] Verify raw input file exists (e.g., `dropship_raw_data.xlsx`).
    - *Fallback:* If missing, raise a explicit `FileNotFoundError` asking the user to provide the raw file path.
  - [ ] Verify template file exists (e.g., `dropship_template.xlsx`).
    - *Fallback:* If missing, raise `FileNotFoundError` prompting the user for the Myntra master template.
  - [ ] Check write permissions for the output target directory.
  - [ ] Detect if files are currently open/locked by Microsoft Excel in Windows (`PermissionError` / file locking). Catch this and display a friendly prompt: *"Please close the Excel file in Excel before running"*.
- [ ] **Sheet Name Resolution**
  - [ ] Raw Data Sheet: Look for sheet name `Raw Data by Gathering`.
    - *Fallback:* If named differently, fall back to the first active sheet (`wb.sheetnames[0]`) and log an informative warning.
  - [ ] Template Sheet: Look for sheet name `MyntraFinal Filled Listing File`.
    - *Fallback:* If named differently, inspect available sheets and select either the single sheet or sheet containing `'Listing'` / `'Template'`.

---

## 2. Template Structure & Header Preservation Checklist

The Myntra template uses a **2-row header structure**:
- **Row 1:** Functional Category Groups (`Business`, `Discoverability`, `Sizing`, `Imagery`).
- **Row 2:** Actual Column / Attribute Names (`styleId`, `styleGroupId`, `vendorSkuCode`, `vendorArticleNumber`, etc.).
- **Row 3+:** Data rows.

- [ ] **Header Parsing Strategy**
  - [ ] Do **not** read template with default `header=0`, as Row 2 column names will be lost or combined incorrectly.
  - [ ] Use `header=1` (0-indexed) when reading the template schema into `pandas.DataFrame`.
  - [ ] Preserve Row 1 and Row 2 in memory or in an `openpyxl` workbook clone so the final exported Excel retains Myntra's exact format.
- [ ] **Raw Data Header Parsing**
  - [ ] Raw data uses standard Row 1 headers (`Parent ID`, `Check`, `Color`, `Size`, `Supplier code`, etc.).
  - [ ] Strip leading/trailing whitespaces from all raw column headers during read.

---

## 3. Schema & Mandatory Column Verification Checklist

If raw data lacks columns needed for mandatory transformations, the script must throw an actionable error showing what is missing and what was found.

- [ ] **Mandatory Columns in Raw Data**
  - [ ] `Check` (Base style/design code, e.g., `BYB180820263F4B`)
  - [ ] `Color` or `Colour` (Variant colour name, e.g., `Green`)
  - [ ] `Size` (Item size, e.g., `S`, `M`, `L`, `XL`, `XXL`)
  - [ ] `Supplier code` (Supplier identifier, e.g., `29865`)
- [ ] **Fuzzy Column Aliasing & Fallbacks**
  - [ ] Detect spelling variants automatically:
    - `Color` $\leftrightarrow$ `Colour` $\leftrightarrow$ `Brand Colour`
    - `Supplier code` $\leftrightarrow$ `SupplierCode` $\leftrightarrow$ `supplier_code` $\leftrightarrow$ `Vendor Code`
    - `Check` $\leftrightarrow$ `Style Code` $\leftrightarrow$ `Design Code`
    - `Product name` $\leftrightarrow$ `Product Name` $\leftrightarrow$ `Title`
  - [ ] If any mandatory column cannot be resolved after alias checks:
    - **Halt execution immediately.**
    - Raise `MissingRequiredColumnError` listing:
      1. Missing required column name(s).
      2. Available columns detected in the uploaded file.
      3. Suggested remediation.

---

## 4. Missing Data & Row-Level Fallbacks Checklist

Handle missing, blank, or malformed values inside individual rows.

- [ ] **Empty Rows Filtering**
  - [ ] Drop rows where all values are `NaN` or empty strings.
  - [ ] Drop rows where `Check` is missing/empty (cannot identify product).
- [ ] **Missing Size Fallback**
  - [ ] If `Size` is null or whitespace:
    - *Option A (Default):* Fall back to `'FS'` (Free Size) or `'ONESIZE'`.
    - *Option B (Strict):* Log a warning with the row index and skip/flag the row.
- [ ] **Missing Colour Fallback**
  - [ ] If `Color` is null:
    - Attempt extraction from `Product name` if pattern matches.
    - If unresolvable, raise validation error or fall back to `'Multi'` / `'Assorted'`.
- [ ] **Missing Supplier Code Fallback**
  - [ ] If `Supplier code` is empty:
    - Look up `Parent ID` or use fallback default code (e.g. `'00000'`).
    - Emit warning log: *"Row {i}: Missing Supplier code; assigned fallback 00000"*.
- [ ] **Whitespace & Case Cleaning**
  - [ ] Apply `.strip()` to all string columns.
  - [ ] Normalize sizes to standard uppercase (`'s'` $\rightarrow$ `'S'`, `'xxl'` $\rightarrow$ `'XXL'`).
  - [ ] Standardize Title Case for colours (`'camel brown'` $\rightarrow$ `'Camel Brown'`).

---

## 5. Business Logic & Column Transformation Checklist

Execute the specific business rules required for Myntra onboarding.

- [ ] **`vendorSkuCode` Generation**
  - [ ] Rule: `f"{Check}_{val}-{Colour}_{val}-{Size}_{val}"` $\rightarrow$ `Check-Colour-Size`.
  - [ ] Example: `BYB180820263F4B-Green-S`.
  - [ ] Sanitize illegal characters: replace slashes `/`, backslashes `\`, and double quotes with hyphens `-` or empty string.
  - [ ] Also populate `SKUCode` in template with this same value.
- [ ] **`vendorArticleNumber` Generation**
  - [ ] Rule: `f"{Check}_{val}-{Colour}_{val}-{Suppliercode}_{val}"` or `Check-Colour-Size-Suppliercode`.
  - [ ] In template sample: Row 3 has `BYB180820263F4B-Green-S-29865`.
  - [ ] Support both:
    - Mode A (Standard): `Check-Colour-Suppliercode`
    - Mode B (Size-specific / Dropship exact match): `Check-Colour-Size-Suppliercode`
- [ ] **`styleGroupId` Generation & Incrementation**
  - [ ] Grouping Key: Unique combination of `(Check, Color)`.
  - [ ] Rule 1: Items of the **same colour** and **same style/check** across **different sizes** MUST retain the **exact same `styleGroupId`**.
  - [ ] Rule 2: Increment the ID by $+1$ each time a new `(Check, Color)` combination appears.
  - [ ] Rule 3: Format the ID as a 3-digit string (e.g. `168`, `169`, or zero-padded `001`, `002` if start < 100).
  - [ ] Parameterize starting ID: Allow configurable `start_style_group_id` (defaulting to e.g. `101` or `168` from template).
- [ ] **Sizing Columns**
  - [ ] Map raw `Size` to `Brand Size`.
  - [ ] Map raw `Size` to `Standard Size`.
  - [ ] Set `is Standard Size present on Label` = `'Yes'`.
- [ ] **Colour Columns**
  - [ ] Map raw `Color` to `Brand Colour (Remarks)`.
  - [ ] Map raw `Color` to `Prominent Colour`.
- [ ] **Image Links Mapping**
  - [ ] Map raw `img1` to `Front Image`.
  - [ ] Map raw `img2` to `Side Image`.
  - [ ] Map raw `img3` to `Back Image`.
  - [ ] Map raw `img4` to `Detail Angle`.
  - [ ] Map raw `img5` to `Look Shot Image`.
  - [ ] Map raw `img6` to `Additional Image 1`.
  - [ ] Map raw `img7` to `Additional Image 2`.
- [ ] **Constant / Default Attributes**
  - [ ] Set `brand` (e.g. `'StyleCast'`).
  - [ ] Set `Manufacturer Name and Address with Pincode`.
  - [ ] Set `Packer Name and Address with Pincode`.
  - [ ] Set `Importer Name and Address with Pincode`.
  - [ ] Set `Country Of Origin` = `'China'` / `'India'`.
  - [ ] Set `AgeGroup` = `'Adults-Women'`.
  - [ ] Set `Net Quantity Unit` = `'Piece'`.
  - [ ] Set `Net Quantity` = `1`.
  - [ ] Set `Year` & `season` (e.g. `2026`, `Winter`).

---

## 6. Output Generation & Formatting Preservation Checklist

Ensure the final `.xlsx` file is valid and accepted by Myntra's catalog ingestion system.

- [ ] **Template Cloning Workflow**
  - [ ] Load `dropship_template.xlsx` using `openpyxl.load_workbook()`.
  - [ ] Retain Row 1 (Category Groups) and Row 2 (Field Headers) intact.
  - [ ] Clear any dummy/sample rows from Row 3 onwards.
  - [ ] Write transformed rows starting at Row 3.
  - [ ] Retain existing column widths, data validation rules, and cell styles where possible.
- [ ] **Data Type Safety**
  - [ ] Ensure `styleGroupId` is written as string or integer according to Myntra specification (prevent scientific notation like `1.68E+02`).
  - [ ] Ensure prices (`MRP`, `ISP`) are formatted as clean numbers without floating-point inaccuracies.
  - [ ] Ensure `HSN` is saved as string to preserve leading zeroes.
- [ ] **Output File Naming & Location**
  - [ ] Default output path: `myntra_matched_output.xlsx` (or timestamped `myntra_matched_output_YYYYMMDD_HHMMSS.xlsx`).
  - [ ] Check output file write success before returning.

---

## 7. Error Handling, Validation & User Feedback Checklist

- [ ] **Pre-Flight Validation Errors (Fatal)**
  - [ ] Missing raw Excel file $\rightarrow$ `MissingInputFileError`.
  - [ ] Missing template Excel file $\rightarrow$ `MissingTemplateFileError`.
  - [ ] Missing required columns $\rightarrow$ `MissingRequiredColumnError`.
  - [ ] Empty raw dataset $\rightarrow$ `EmptyDatasetError`.
- [ ] **Row-Level Warnings (Non-Fatal)**
  - [ ] Log warning when fallback size or fallback colour is used.
  - [ ] Log warning when image URL is missing or malformed.
  - [ ] Collect all warnings into an execution summary report.
- [ ] **Execution Summary Statistics**
  - [ ] Total raw rows read.
  - [ ] Total template rows generated.
  - [ ] Total unique `styleGroupId` values generated.
  - [ ] Total unique styles (`Check`) processed.
  - [ ] Output file path and size.

---

## 8. Modular Architecture Blueprint

Structure the codebase into a clean, reusable OOP design:

```
Excel-Matcher/
├── dropship_raw_data.xlsx       # Input Raw Data
├── dropship_template.xlsx       # Input Master Template
├── myntra_matched_output.xlsx   # Output Generated Template
├── myntra-matching.py           # Core MyntraMatching Class & CLI
└── EXCEL_MAPPING_PLAN.md        # This Plan & Checklist
```

### Class Structure (`MyntraMatching`):
```python
class MyntraMatching:
    def __init__(self, raw_path: str, template_path: str, output_path: str, start_style_id: int = 168):
        ...
    def validate_files(self) -> None:
        """Checks file existence and accessibility."""
        ...
    def load_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Loads raw data and template headers."""
        ...
    def validate_columns(self, raw_df: pd.DataFrame) -> dict[str, str]:
        """Resolves required columns with alias checking."""
        ...
    def generate_style_group_ids(self, raw_df: pd.DataFrame, check_col: str, color_col: str) -> pd.Series:
        """Assigns 3-digit styleGroupId per (Check, Color) with sequential +1 increment."""
        ...
    def transform(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """Executes mapping logic to populate template structure."""
        ...
    def export(self, output_df: pd.DataFrame) -> str:
        """Writes data into cloned template preserving multi-row headers."""
        ...
    def run(self) -> str:
        """Full execution pipeline with validation and logging."""
        ...
```

---

## 9. Verification & Testing Checklist

- [ ] Run test on provided sample files (`dropship_raw_data.xlsx` and `dropship_template.xlsx`).
- [ ] Verify that `vendorSkuCode` equals `Check-Colour-Size`.
- [ ] Verify that all sizes of the same style + colour have the **same `styleGroupId`**.
- [ ] Verify that when colour changes or style changes, `styleGroupId` increments by **+1**.
- [ ] Verify that every `styleGroupId` is 3 digits.
- [ ] Open generated Excel file and verify Row 1 (Groups) and Row 2 (Columns) are visually intact.
- [ ] Test negative cases:
  - [ ] Missing raw file triggers clear error.
  - [ ] Missing required column triggers clear error with hints.
