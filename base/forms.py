from django import forms
from .models import Restaurant

class RestaurantCreateForm(forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = [
            'name',
            'description',
            'address',
            'phone',
            'email',
            'logo',
            'cover_image',
            'primary_color',
            'secondary_color',
        ]

        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'primary_color': forms.TextInput(attrs={'type': 'color'}),
            'secondary_color': forms.TextInput(attrs={'type': 'color'}),
        }

# forms.py
from django import forms
from .models import Order, OrderItem, MenuItem, Table


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['order_type', 'table', 'customer_name', 'customer_phone', 'notes']
        widgets = {
            'order_type': forms.Select(attrs={'class': 'form-control'}),
            'table': forms.Select(attrs={'class': 'form-control'}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        # Extraire 'restaurant' des kwargs avant d'appeler super()
        self.restaurant = kwargs.pop('restaurant', None)
        super().__init__(*args, **kwargs)
        
        if self.restaurant:
            self.fields['table'].queryset = Table.objects.filter(
                restaurant=self.restaurant, 
                is_active=True
            ).order_by('number')
class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['menu_item', 'quantity']
        widgets = {
            'menu_item': forms.HiddenInput(),
            'quantity': forms.NumberInput(attrs={'min': 1})
        }

# Configuration du FormSet
OrderItemFormSet = forms.inlineformset_factory(
    Order,
    OrderItem,
    form=OrderItemForm,
    extra=0,
    can_delete=True,
    min_num=1,
    validate_min=True
)

class TableForm(forms.ModelForm):
    class Meta:
        model = Table
        fields = ['number', 'capacity']