"""
Kalkulator Sederhana
Menyediakan operasi penjumlahan, pengurangan, perkalian, dan pembagian.
"""


def tambah(a, b):
    return a + b


def kurang(a, b):
    return a - b


def kali(a, b):
    return a * b


def bagi(a, b):
    if b == 0:
        raise ValueError("Tidak bisa membagi dengan nol!")
    return a / b


def hitung(angka1, operator, angka2):
    """Menghitung hasil berdasarkan operator yang dipilih."""
    operasi = {
        "+": tambah,
        "-": kurang,
        "*": kali,
        "/": bagi,
    }

    if operator not in operasi:
        raise ValueError(f"Operator '{operator}' tidak dikenal!")

    return operasi[operator](angka1, angka2)


def main():
    print("=== Kalkulator Sederhana ===")
    print("Operasi: +, -, *, /")
    print("Ketik 'keluar' untuk berhenti.\n")

    while True:
        perintah = input("Masukkan perintah (contoh: 5 + 3, atau 'keluar'): ")
        if perintah.lower() == "keluar":
            print("Terima kasih! Sampai jumpa.")
            break

        try:
            bagian = perintah.split()
            angka1 = float(bagian[0])
            operator = bagian[1]
            angka2 = float(bagian[2])
            hasil = hitung(angka1, operator, angka2)
            print(f"Hasil: {angka1} {operator} {angka2} = {hasil}\n")
        except (ValueError, IndexError):
            print("⚠️  Perintah tidak valid. Gunakan format: angka1 operator angka2\n")


if __name__ == "__main__":
    main()