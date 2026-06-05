import akshare as ak

print("Searching for macro APIs:")
macros = [m for m in dir(ak) if 'macro' in m]
print(f"Total macro APIs: {len(macros)}")
print("Some relevant macro APIs:")
for m in macros:
    if 'bdi' in m or 'ccfi' in m or 'index' in m or 'price' in m or 'commodity' in m or 'china' in m:
        print(f" - {m}")

print("\nSearching for profit forecast / research report APIs:")
reports = [m for m in dir(ak) if 'profit' in m or 'forecast' in m or 'report' in m or 'research' in m or 'rating' in m or 'yq' in m or 'yj' in m]
print(f"Total report APIs: {len(reports)}")
for r in reports:
    print(f" - {r}")
