import os


folder_path = os.getcwd()


for file_name in os.listdir(folder_path):

    if file_name.endswith('.png'):

        base_name = os.path.splitext(file_name)[0]
        txt_file_path = os.path.join(folder_path, base_name + '.txt')

        if not os.path.exists(txt_file_path):
            with open(txt_file_path, 'w') as txt_file:
                pass
            print(f"Создан пустой файл: {txt_file_path}")
